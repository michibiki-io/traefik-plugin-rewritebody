---
name: Bug report
about: Create a report to help us improve
title: ''
labels: ''
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**Relevant Config**
Any specific information about regex used. Specific information about
HTTP query would be appreciated as well!

**Expected behavior**
A clear and concise description of what you expected to happen.


**Actual behavior**
A clear and concise description of what actually happened.

**Logs**
Include the Traefik startup logs and any logs recorded while reproducing the issue.

You can add the following to your Traefik config:
```yaml
log:
  level: DEBUG
```

Look for the `Loading plugins...` and `Plugins loaded.` messages at startup.
Include the plugin name you configured and its module name
(`github.com/michibiki-io/traefik-plugin-rewritebody`).

**Server (please complete the following information):**
 - OS: [e.g. Docker, Ubuntu]
 - Traefik Version [e.g. 2.6]
 - Plugin Version [e.g. 0.5.0]

**Additional context**
Add any other context about the problem here.
