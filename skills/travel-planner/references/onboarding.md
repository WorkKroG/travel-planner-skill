# Onboarding and resuming

One trip uses one explicit trip workspace. Recommend a separate folder and local Codex project before writing: this isolates sources and decisions, supports several focused chats, and makes archival safe. Project creation is the user's action in v0.1.0; explain how to choose/add the folder but do not claim to have created or switched a project.

For a new trip, first check that the chosen folder is neither the skill source nor an existing trip. Confirm the exact path and title with the user, then initialize only after that confirmation:

```bash
travel-planner init PATH --title "TITLE" --trip-id TRIP_ID --confirm-path
```

`--confirm-path` is deliberate. Do not initialize in a skill-development repository, overwrite state, or infer dates. A user may deliberately use a chosen folder without a separate project; name it as an advanced mode and still require the path confirmation.

For continuation, a valid `brief.yaml` and its stable `trip_id` identify a workspace. When more than one workspace is available, ask the user to name a path or `trip_id`; do not select the newest. Read the canonical YAML and decision/source files, then validate before editing:

```bash
travel-planner validate PATH
```

HTML and PDF are derived views, never a substitute for state. Resume from the affected files and explain any scoped rebuild that a later change will require.
