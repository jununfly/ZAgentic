<!-- ROADMAP_SECTION_START -->
## ZJ Roadmap

> 数据文件: `roadmap-zj-composer.json` | 最后更新: 2026-10-09 13:58:59

[~][Y+] 1. Composer implementation and reversible PoC
├── [x][Y+] 1-1. Freeze Composer and Plan contracts
│   ├── [x][Y+] 1-1-1. Define built-in Plan template v1
│   ├── [x][Y+] 1-1-2. Define capability-index and provenance-snapshot rules
│   └── [x][Y+] 1-1-3. Define required-skill gap protocol and Plan status transitions
├── [x][Y+] 1-2. Scaffold the public Composer skill
│   ├── [x][Y+] 1-2-1. Add Composer frontmatter and explicit invocation contract
│   └── [x][Y+] 1-2-2. Bundle the Plan template and supporting references
├── [~][Y+] 1-3. Build capability index and provenance snapshot
│   ├── [x][Y+] 1-3-1. Discover the recursive public-skill catalog
│   └── [ ][Y+] 1-3-2. Generate revisioned capability snapshots and metadata warnings
├── [ ][Y+] 1-4. Implement the Plan validator seam
│   ├── [!][Y+] 1-4-1. Validate Plan schema, provenance, and selection reasons
│   └── [!][Y+] 1-4-2. Validate gaps, prerequisites, authority, and side-effect boundaries
├── [ ][Y+] 1-5. Build external repository research fixture
│   ├── [!][Y+] 1-5-1. Freeze external-repository-research fixture inputs and oracle
│   └── [!][Y+] 1-5-2. Generate and validate the research Plan output
├── [ ][Y+] 1-6. Build tool-combination design fixture
│   ├── [!][Y+] 1-6-1. Freeze tool-combination-design fixture inputs and oracle
│   └── [!][Y+] 1-6-2. Generate and validate the combination Plan output
├── [ ][Y+] 1-7. Add security, oracle, handoff, and removal regression checks
│   ├── [!][Y+] 1-7-1. Add negative-case and Human-rejection checks
│   └── [!][Y+] 1-7-2. Add security, handoff, and removal-regression checks
└── [!][Y+] 1-8. Human review of PoC evidence and continuation decision
<details><summary>阻塞链：9 个节点被阻塞</summary>

- 1-4-1. Validate Plan schema, provenance, and selection reasons ← e8: 1-3-2. Generate revisioned capability snapshots and metadata warnings [ ]
- 1-4-2. Validate gaps, prerequisites, authority, and side-effect boundaries ← e11: 1-4-1. Validate Plan schema, provenance, and selection reasons [ ]
- 1-5-1. Freeze external-repository-research fixture inputs and oracle ← e9: 1-3-2. Generate revisioned capability snapshots and metadata warnings [ ]
- 1-5-2. Generate and validate the research Plan output ← e12: 1-4-2. Validate gaps, prerequisites, authority, and side-effect boundaries [ ], e14: 1-5-1. Freeze external-repository-research fixture inputs and oracle [ ]
- 1-6-1. Freeze tool-combination-design fixture inputs and oracle ← e10: 1-3-2. Generate revisioned capability snapshots and metadata warnings [ ]
- ... 另有 4 个节点被阻塞未列出

</details>


### 下一步可开工（ready 前 3）

- 1-3-2. Generate revisioned capability snapshots and metadata warnings [ ]
- 1-4. Implement the Plan validator seam [ ]
- 1-5. Build external repository research fixture [ ]
<!-- ROADMAP_SECTION_END -->
