# RMF Load Lab

## Français

Banc d’essai **boîte noire** pour un programme d’enchères de flotte. Il mesure la latence p95, la mémoire résidente maximale et les délais dépassés lorsque le nombre de robots et la profondeur des files augmentent. Le fichier d’exemple exécute un faux candidat déterministe : il valide le banc, **pas Open-RMF**.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/rmf-load-lab fixtures/scenarios.json --locale=fr -- .venv/bin/python fixtures/fake_bidder.py '{scenario}'
```

Pour tester Open-RMF, fournir un exécutable local qui lit le JSON du chemin `{scenario}`, effectue une enchère sur un environnement de test et écrit `{"accepted":true}` sur stdout. Le banc lance cet exécutable comme processus séparé, mesure son arbre de processus et le termine au délai configuré. Ne passer qu’une commande de confiance, sur un système de test isolé : le banc ne garantit pas qu’un adaptateur externe n’envoie pas de vraie tâche. Les seuils de l’exemple sont illustratifs. La mémoire n’est mesurée que pour l’arbre du processus lancé ; une mémoire indisponible donne `inconclusive`.

Codes de sortie : 0 `pass`, 1 `fail`, 2 entrée invalide, 3 `inconclusive`.

## English

**Black-box** load harness for a fleet bidding executable. It measures p95 latency, peak resident memory and timeouts as robot count and queue depth grow. The example runs a deterministic fake bidder: it validates the harness, **not Open-RMF**.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/rmf-load-lab fixtures/scenarios.json --locale=en -- .venv/bin/python fixtures/fake_bidder.py '{scenario}'
```

To test Open-RMF, supply a local executable that reads JSON at `{scenario}`, bids in a test environment, and writes `{"accepted":true}` to stdout. The harness starts it as a separate process, measures its process tree and terminates it at the configured timeout. Only pass trusted commands on an isolated test system: the harness cannot guarantee an external adapter will not submit a real task. Example thresholds are illustrative. Memory is measured only for the spawned process tree; unavailable memory yields `inconclusive`.

Exit codes: 0 `pass`, 1 `fail`, 2 invalid input, 3 `inconclusive`.

## Español

Banco de carga de **caja negra** para un ejecutable de ofertas de flota. Mide latencia p95, pico de memoria residente y tiempos agotados al aumentar robots y profundidad de cola. El ejemplo ejecuta un candidato simulado determinista: valida el banco, **no Open-RMF**.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/rmf-load-lab fixtures/scenarios.json --locale=es -- .venv/bin/python fixtures/fake_bidder.py '{scenario}'
```

Para probar Open-RMF, proporciona un ejecutable local que lea el JSON en `{scenario}`, haga una oferta en un entorno de prueba y escriba `{"accepted":true}` en stdout. El banco lo inicia como proceso separado, mide su árbol de procesos y lo termina al agotarse el tiempo configurado. Usa solo comandos de confianza en un sistema de prueba aislado: el banco no puede garantizar que un adaptador externo no envíe una tarea real. Los límites del ejemplo son ilustrativos. La memoria solo se mide en el árbol del proceso iniciado; si no está disponible, el resultado es `inconclusive`.

Códigos de salida: 0 `pass`, 1 `fail`, 2 entrada no válida, 3 `inconclusive`.

MIT — [LICENSE](LICENSE).
