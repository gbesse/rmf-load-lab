"""Black-box load harness for a fleet bidding executable."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import psutil


MESSAGES = {
    "fr": {"timeout": "Délai dépassé pour {name}", "exit": "Le candidat a échoué pour {name}", "rejected": "Tâche rejetée pour {name}", "latency": "Latence au-dessus du seuil pour {name}", "memory": "Mémoire au-dessus du seuil pour {name}", "unknown_memory": "Mesure de mémoire indisponible pour {name}", "input": "Entrée invalide", "summary": "{scenarios} scénario(s), {failures} échec(s), {unknown} non vérifié(s)"},
    "en": {"timeout": "Timeout for {name}", "exit": "Bidder failed for {name}", "rejected": "Task rejected for {name}", "latency": "Latency above limit for {name}", "memory": "Memory above limit for {name}", "unknown_memory": "Memory measurement unavailable for {name}", "input": "Invalid input", "summary": "{scenarios} scenario(s), {failures} failure(s), {unknown} unverified"},
    "es": {"timeout": "Tiempo agotado para {name}", "exit": "El candidato falló para {name}", "rejected": "Tarea rechazada para {name}", "latency": "Latencia superior al límite para {name}", "memory": "Medición de memoria superior al límite para {name}", "unknown_memory": "Medición de memoria no disponible para {name}", "input": "Entrada no válida", "summary": "{scenarios} escenario(s), {failures} fallo(s), {unknown} sin verificar"},
}


def validate_scenarios(scenarios):
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios")
    names = set()
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {"name", "robots", "queue_depth", "requests", "repetitions", "timeout_ms", "max_p95_ms", "max_rss_mb"}:
            raise ValueError("scenario fields")
        name = scenario["name"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("scenario name")
        names.add(name)
        for field in ("robots", "queue_depth", "requests", "repetitions", "timeout_ms"):
            value = scenario[field]
            if not isinstance(value, int) or isinstance(value, bool) or value <= (0 if field != "queue_depth" else -1):
                raise ValueError(field)
        for field in ("max_p95_ms", "max_rss_mb"):
            value = scenario[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(field)
    return scenarios


def _rss_tree(process):
    try:
        return sum(item.memory_info().rss for item in [process, *process.children(recursive=True)] if item.is_running())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def _kill_group(process):
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGKILL)
    else:
        process.kill()


def run_once(scenario, command):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "scenario.json"
        path.write_text(json.dumps({key: scenario[key] for key in ("name", "robots", "queue_depth", "requests")}), encoding="utf-8")
        argv = [item.replace("{scenario}", str(path)) for item in command]
        output = Path(directory) / "stdout.txt"
        errors = Path(directory) / "stderr.txt"
        start = time.monotonic()
        with output.open("wb") as stdout, errors.open("wb") as stderr:
            process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
            observed = psutil.Process(process.pid)
            peak = None
            deadline = start + scenario["timeout_ms"] / 1000
            timed_out = False
            while process.poll() is None:
                rss = _rss_tree(observed)
                peak = rss if peak is None else max(peak, rss or 0)
                if time.monotonic() >= deadline:
                    timed_out = True
                    _kill_group(process)
                    break
                time.sleep(0.005)
            process.wait()
        elapsed_ms = (time.monotonic() - start) * 1000
        try:
            result = json.loads(output.read_text(encoding="utf-8")) if not timed_out and process.returncode == 0 else None
        except (UnicodeError, ValueError):
            result = None
        accepted = result.get("accepted") if isinstance(result, dict) else None
        return {"duration_ms": round(elapsed_ms, 3), "peak_rss_mb": round(peak / 1048576, 3) if peak is not None else None, "exit_code": process.returncode, "timeout": timed_out, "accepted": accepted if isinstance(accepted, bool) else None, "stderr_tail": errors.read_text(encoding="utf-8", errors="replace")[-500:]}


def _finding(locale, code, name):
    return {"code": code, "scenario": name, "message": MESSAGES[locale][code].format(name=name)}


def audit(scenarios, command, locale="en"):
    if locale not in MESSAGES:
        raise ValueError("locale")
    validate_scenarios(scenarios)
    if not isinstance(command, list) or not command or not any("{scenario}" in part for part in command):
        raise ValueError("command requires {scenario}")
    results = []
    findings = []
    for scenario in scenarios:
        runs = [run_once(scenario, command) for _ in range(scenario["repetitions"])]
        durations = sorted(run["duration_ms"] for run in runs)
        p95 = durations[max(0, -(-95 * len(durations) // 100) - 1)]
        memory = max((run["peak_rss_mb"] for run in runs if run["peak_rss_mb"] is not None), default=None)
        local = []
        if any(run["timeout"] for run in runs):
            local.append(_finding(locale, "timeout", scenario["name"]))
        if any(run["exit_code"] != 0 or run["accepted"] is None for run in runs):
            local.append(_finding(locale, "exit", scenario["name"]))
        if any(run["accepted"] is False for run in runs):
            local.append(_finding(locale, "rejected", scenario["name"]))
        if p95 > scenario["max_p95_ms"]:
            local.append(_finding(locale, "latency", scenario["name"]))
        if memory is None:
            local.append(_finding(locale, "unknown_memory", scenario["name"]))
        elif memory > scenario["max_rss_mb"]:
            local.append(_finding(locale, "memory", scenario["name"]))
        status = "fail" if any(item["code"] != "unknown_memory" for item in local) else "inconclusive" if local else "pass"
        results.append({"name": scenario["name"], "robots": scenario["robots"], "queue_depth": scenario["queue_depth"], "p95_ms": p95, "peak_rss_mb": memory, "status": status, "runs": runs, "findings": local})
        findings.extend(local)
    failures = sum(item["status"] == "fail" for item in results)
    unknown = sum(item["status"] == "inconclusive" for item in results)
    return {"format": "rmf-load-lab/v1", "locale": locale, "status": "fail" if failures else "inconclusive" if unknown else "pass", "summary": MESSAGES[locale]["summary"].format(scenarios=len(results), failures=failures, unknown=unknown), "scenarios": results, "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fleet bid load test / Charge des enchères de flotte / Carga de ofertas de flota")
    parser.add_argument("scenarios")
    parser.add_argument("--locale", choices=MESSAGES, default="en")
    parser.add_argument("--output")
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        parser.error("command separator -- required / séparateur -- requis / separador -- obligatorio")
    separator = argv.index("--")
    command = argv[separator + 1:]
    args = parser.parse_args(argv[:separator])
    try:
        raw = Path(args.scenarios).read_bytes()
        report = audit(json.loads(raw), command, args.locale)
        report["source"] = {"path": args.scenarios, "sha256": hashlib.sha256(raw).hexdigest()}
        report["command"] = command
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(f"{MESSAGES[args.locale]['input']}: {exc if args.locale == 'en' else type(exc).__name__}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return {"pass": 0, "fail": 1, "inconclusive": 3}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
