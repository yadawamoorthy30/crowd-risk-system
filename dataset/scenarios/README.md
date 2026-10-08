# Scenarios

| Folder | What N(t) should look like | Used later for |
|---|---|---|
| `steady` | Roughly constant | Checking the system does NOT raise false alarms |
| `rapid_growth` | Climbs quickly over seconds to minutes | Growth-rate and early warning |
| `surge` | Sudden jump (e.g. a gate opens) | Alert latency |
| `dispersal` | Falls steadily | Alerts clearing correctly |

Put clips in the matching folder, or list them in `manifest.csv` if the clip lives in
`evaluation_clips/` and only a time range of it shows the scenario.
