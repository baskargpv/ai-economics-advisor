# AI Economics Advisor (Python/Streamlit)

Right-size an AI/LLM use case before you build it. Describe the use case and
expected volume — this tool estimates inference cost, total cost of
ownership, ROI, and cost per successful outcome, and recommends the simplest
architecture that meets the requirement.

Pure Python calculation engine, Streamlit UI, deployed free on Streamlit
Community Cloud. No backend infrastructure beyond that, no data collection,
no API keys required to use it.

## Status

✅ Live: **https://ai-economics-advisor.streamlit.app**

1. ✅ Project scaffold (this)
2. ✅ Data layer — `data/pricing.json`, `data/usecases.json`
3. ✅ Engine layer — pure functions in `engine/`, tested with pytest
4. ✅ Form UI — Streamlit widgets for the progressive question flow (`ui/form.py`)
5. ✅ Results UI — assessment / comparison screen (`ui/results.py`)
6. ✅ Wire together + test against worked example end-to-end (`engine/pipeline.py`, `tests/test_pipeline.py`)
7. ✅ Deploy to Streamlit Community Cloud

## Local development

```bash
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py            # local dev server
pytest                           # run engine unit tests
```

## Project structure

```
data/            # versioned pricing + use-case config (source of truth)
engine/          # pure calculation functions — no side effects, fully testable
ui/              # Streamlit widgets — form input collection and results rendering
tests/           # pytest unit tests
app.py           # Streamlit entry point
```

## Deployment

- **Source of truth:** this GitHub repo.
- **Live demo:** https://ai-economics-advisor.streamlit.app — deployed via
  Streamlit Community Cloud, connected directly to this repo — no GitHub
  Action needed, Streamlit rebuilds on every push to `main`.

## Data sourcing

Pricing is seeded from and periodically diffed against
[LiteLLM's `model_prices_and_context_window.json`](https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json)
(MIT licensed), then manually reviewed before being merged into
`data/pricing.json`.

## License

MIT
