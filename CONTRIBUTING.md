# Contributing

Create a focused branch and pull request. Include the behavior change, safety impact, tests run, and screenshots for UI changes. Never fabricate Qodo evidence. Changes to approval gates, trace evaluation, release decisions, fixture boundaries, or external-write adapters require regression tests and explicit review.

Run `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v` from the repository root and `npm --prefix frontend run build` before requesting review.
