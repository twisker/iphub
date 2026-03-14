# IpHub — IpMan Skill Registry

> Reference registry for [IpMan](https://github.com/twisker/ipman) skills and IP packages.

IpHub is a **reference-only registry** — it stores metadata about skills, not the skills themselves. All installations go through agent native CLI commands.

## Top Skills

<!-- TOP_SKILLS_START -->
*No data yet. Rankings will appear after the first stats collection.*
<!-- TOP_SKILLS_END -->

## Top Packages

<!-- TOP_PACKAGES_START -->
*No data yet.*
<!-- TOP_PACKAGES_END -->

## Top 50

<!-- TOP_ALL_START -->
*No data yet.*
<!-- TOP_ALL_END -->

## How It Works

1. **Publish**: `ipman hub publish <skill>` creates a PR to this repo
2. **Install**: `ipman install <name>` looks up this registry, then calls agent CLI
3. **Stats**: Install counts tracked via GitHub Issues (counter labels)
4. **Mirror**: CNB mirror at `cnb.cool/lutuai/twisker/iphub`

## Structure

```
iphub/
├── index.yaml              # Auto-generated index (skills + packages)
├── registry/
│   └── @<owner>/           # Per-author namespace
│       ├── <skill>.yaml    # Skill registration
│       └── <package>/      # IP package (versioned)
│           ├── meta.yaml
│           └── <version>.yaml
└── stats/
    ├── downloads.yaml      # Raw stats
    ├── top-10-skills.md    # Embeddable ranking
    ├── top-10-packages.md
    └── top-50-all.md
```

## Links

- [IpMan](https://github.com/twisker/ipman) — The CLI tool
- [Documentation](https://twisker.github.io/ipman)
- [IpHub Design](https://github.com/twisker/ipman/blob/main/.claude/research/iphub-design.md)
