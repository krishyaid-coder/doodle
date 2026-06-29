/**
 * doodle VS Code extension.
 *
 * Shells out to the `doodle` CLI on SKILL.md changes, parses --format=json,
 * surfaces findings as VS Code diagnostics. Offers a quick-fix code action
 * for rules with fixable=true.
 *
 * No bundled language server — the CLI does the real work. Keeps this
 * extension tiny and lets users run any doodle version they want.
 */

import * as vscode from "vscode";
import { spawn } from "child_process";

const DIAGNOSTIC_SOURCE = "doodle";
const SKILL_FILE_PATTERN = /SKILL\.md$/;

// Mirror src/doodle/fixers.py FIXERS keys. If new fixers ship in doodle,
// update this set so the extension offers quick-fixes for them.
const FIXABLE_RULES = new Set<string>([
  "hygiene/desc-blank-lines",
  "body/emoji",
]);

interface DoodleFinding {
  rule_id: string;
  severity: "error" | "warning" | "info";
  file: string;
  line: number;
  column: number;
  message: string;
  suggestion: string | null;
}

let diagnosticCollection: vscode.DiagnosticCollection;
const debounceTimers = new Map<string, NodeJS.Timeout>();

export function activate(context: vscode.ExtensionContext): void {
  diagnosticCollection = vscode.languages.createDiagnosticCollection(DIAGNOSTIC_SOURCE);
  context.subscriptions.push(diagnosticCollection);

  // Lint any SKILL.md files already open
  vscode.workspace.textDocuments.forEach(maybeLint);

  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(maybeLint),
    vscode.workspace.onDidSaveTextDocument(maybeLint),
    vscode.workspace.onDidChangeTextDocument((e) => {
      const cfg = vscode.workspace.getConfiguration("doodle");
      if (cfg.get<string>("runOn") !== "change") {return;}
      const doc = e.document;
      if (!isSkillFile(doc)) {return;}
      const key = doc.uri.toString();
      const prev = debounceTimers.get(key);
      if (prev) {clearTimeout(prev);}
      const delay = cfg.get<number>("debounceMs") ?? 400;
      debounceTimers.set(
        key,
        setTimeout(() => {
          debounceTimers.delete(key);
          void lintDocument(doc);
        }, delay),
      );
    }),
    vscode.workspace.onDidCloseTextDocument((doc) => {
      diagnosticCollection.delete(doc.uri);
    }),
  );

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("doodle.lintCurrentFile", async () => {
      const doc = vscode.window.activeTextEditor?.document;
      if (doc && isSkillFile(doc)) {await lintDocument(doc);}
      else {vscode.window.showInformationMessage("doodle: open a SKILL.md file first.");}
    }),
    vscode.commands.registerCommand("doodle.fixCurrentFile", async () => {
      const doc = vscode.window.activeTextEditor?.document;
      if (!doc || !isSkillFile(doc)) {
        vscode.window.showInformationMessage("doodle: open a SKILL.md file first.");
        return;
      }
      await doc.save();
      try {
        await runDoodleFix(doc.uri.fsPath);
        vscode.window.showInformationMessage("doodle: auto-fixes applied.");
        await lintDocument(doc);
      } catch (err) {
        vscode.window.showErrorMessage(`doodle --fix failed: ${err}`);
      }
    }),
    vscode.commands.registerCommand("doodle.explainRule", async () => {
      const ruleId = await vscode.window.showInputBox({
        prompt: "Rule ID to explain (e.g. desc/too-long)",
        placeHolder: "desc/too-long",
      });
      if (!ruleId) {return;}
      try {
        const out = await runDoodleExplain(ruleId);
        const channel = vscode.window.createOutputChannel("doodle");
        channel.clear();
        channel.appendLine(out);
        channel.show();
      } catch (err) {
        vscode.window.showErrorMessage(`doodle --explain failed: ${err}`);
      }
    }),
  );

  // Quick-fix code actions
  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      { language: "markdown", pattern: "**/SKILL.md" },
      new DoodleCodeActionProvider(),
      { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] },
    ),
  );
}

export function deactivate(): void {
  diagnosticCollection?.dispose();
  debounceTimers.forEach((t) => clearTimeout(t));
  debounceTimers.clear();
}

function isSkillFile(doc: vscode.TextDocument): boolean {
  return SKILL_FILE_PATTERN.test(doc.fileName);
}

function maybeLint(doc: vscode.TextDocument): void {
  if (isSkillFile(doc)) {void lintDocument(doc);}
}

async function lintDocument(doc: vscode.TextDocument): Promise<void> {
  try {
    const findings = await runDoodleJson(doc.uri.fsPath);
    diagnosticCollection.set(doc.uri, findings.map((f) => toDiagnostic(f, doc)));
  } catch (err) {
    diagnosticCollection.set(doc.uri, [
      {
        range: new vscode.Range(0, 0, 0, 1),
        message: `doodle could not run: ${err}\nCheck the 'doodle.command' setting.`,
        severity: vscode.DiagnosticSeverity.Error,
        source: DIAGNOSTIC_SOURCE,
      },
    ]);
  }
}

function toDiagnostic(f: DoodleFinding, doc: vscode.TextDocument): vscode.Diagnostic {
  const lineNo = Math.max(0, (f.line || 1) - 1);
  const lineText = lineNo < doc.lineCount ? doc.lineAt(lineNo).text : "";
  const startCol = Math.max(0, (f.column || 1) - 1);
  const endCol = lineText.length > startCol ? lineText.length : startCol + 1;
  const range = new vscode.Range(lineNo, startCol, lineNo, endCol);

  const sev: vscode.DiagnosticSeverity = {
    error: vscode.DiagnosticSeverity.Error,
    warning: vscode.DiagnosticSeverity.Warning,
    info: vscode.DiagnosticSeverity.Information,
  }[f.severity] ?? vscode.DiagnosticSeverity.Warning;

  const messageParts = [f.message];
  if (f.suggestion) {messageParts.push("→ " + f.suggestion);}
  if (FIXABLE_RULES.has(f.rule_id)) {messageParts.push("(fixable: doodle --fix)");}
  const diag = new vscode.Diagnostic(range, messageParts.join("\n"), sev);
  diag.source = DIAGNOSTIC_SOURCE;
  diag.code = {
    value: f.rule_id,
    target: vscode.Uri.parse(`https://github.com/krishyaid-coder/doodle/blob/main/RULES.md`),
  };
  return diag;
}

function runDoodleJson(filePath: string): Promise<DoodleFinding[]> {
  const cfg = vscode.workspace.getConfiguration("doodle");
  const command = cfg.get<string>("command") || "doodle";
  const args = [filePath, "--format=json", "--no-color"];
  if (cfg.get<boolean>("strict")) {args.push("--strict");}
  const configPath = cfg.get<string>("configFile");
  if (configPath) {args.push("--config", configPath);}
  return execJson(command, args);
}

function runDoodleFix(filePath: string): Promise<void> {
  const cfg = vscode.workspace.getConfiguration("doodle");
  const command = cfg.get<string>("command") || "doodle";
  return new Promise((resolve, reject) => {
    const proc = spawn(command, [filePath, "--fix", "--no-color"]);
    let stderr = "";
    proc.stderr.on("data", (d) => (stderr += d.toString()));
    proc.on("close", (code) => {
      if (code === 3) {reject(new Error(stderr.trim() || `exit ${code}`));}
      else {resolve();}
    });
    proc.on("error", reject);
  });
}

function runDoodleExplain(ruleId: string): Promise<string> {
  const cfg = vscode.workspace.getConfiguration("doodle");
  const command = cfg.get<string>("command") || "doodle";
  return new Promise((resolve, reject) => {
    const proc = spawn(command, ["--explain", ruleId]);
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));
    proc.on("close", (code) => {
      if (code === 3 || !stdout.trim()) {reject(new Error(stderr.trim() || `exit ${code}`));}
      else {resolve(stdout);}
    });
    proc.on("error", reject);
  });
}

function execJson(command: string, args: string[]): Promise<DoodleFinding[]> {
  return new Promise((resolve, reject) => {
    const proc = spawn(command, args);
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));
    proc.on("close", (code) => {
      // doodle exit codes: 0 clean, 1 warnings, 2 errors, 3 tool error.
      // For 0/1/2 we still get valid JSON.
      if (code === 3) {
        reject(new Error(stderr.trim() || "tool error"));
        return;
      }
      const trimmed = stdout.trim();
      if (!trimmed) {
        resolve([]);
        return;
      }
      try {
        resolve(JSON.parse(trimmed));
      } catch (e) {
        reject(new Error(`invalid JSON from doodle: ${(e as Error).message}`));
      }
    });
    proc.on("error", (e) => reject(new Error(`could not spawn '${command}': ${e.message}`)));
  });
}

class DoodleCodeActionProvider implements vscode.CodeActionProvider {
  provideCodeActions(
    _doc: vscode.TextDocument,
    _range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
  ): vscode.CodeAction[] {
    const actions: vscode.CodeAction[] = [];
    for (const diag of context.diagnostics) {
      if (diag.source !== DIAGNOSTIC_SOURCE) {continue;}
      const ruleId =
        typeof diag.code === "object" && diag.code && "value" in diag.code
          ? String((diag.code as { value: string | number }).value)
          : String(diag.code ?? "");
      if (!FIXABLE_RULES.has(ruleId)) {continue;}
      const action = new vscode.CodeAction(
        `Fix with doodle (${ruleId})`,
        vscode.CodeActionKind.QuickFix,
      );
      action.command = {
        command: "doodle.fixCurrentFile",
        title: "Run doodle --fix on this file",
      };
      action.diagnostics = [diag];
      action.isPreferred = true;
      actions.push(action);
    }
    return actions;
  }
}
