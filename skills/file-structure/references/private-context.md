# Private development context

Use this pattern when confidential originals, attachments, analysis or excerpts need local version history beside a public project. The project defines what may be published from the content and the owner's intent; a personal detail or a short excerpt is not automatically public or private. This pattern works independently of any memory tool.

## Minimal structure and boundaries

```text
project/
  .git/                         Public repository
  .gitignore                    Ignores /private/
  devDoc/                       Public guidance and the single public task state
  private/
    .git/                       Complete independent local repository
    .gitignore                  Private repository's own disposable/generated files
    README.md                   Local index and backup/recovery entry point
    sources/context-001/        Confidential originals and adjacent attachments
    devDoc/tasks/<task-key>/     Confidential evidence for the same public task key
    tmp/                        Disposable confidential derivatives
    artifacts/                  Selected confidential evidence and outputs
```

Create only the parts with real content. Combine the [development documentation](dev-docs.md) and [experiment](experiment-packages.md) patterns as needed: the public tree owns plans, progress and delivery conclusions; the private tree supplies confidential context without mirroring that state. Confidentiality chooses the boundary first; purpose and retention then choose a location within it.

The outer repository ignores the whole `/private/` tree. The inner repository has its own objects, index and history; keep it independent of the public Git storage rather than registering a submodule, gitlink or worktree. Address each repository explicitly when inspecting or committing. Keep its initial use local, with no inherited public remote or automatic upload. Record an actual separate backup location and recovery steps, including needed originals and attachments ignored by the inner Git; local Git history alone is not an independent backup.

These are version and publication boundaries, not encryption or access control. Whole-directory archives, explicit exports, synchronization and tool transfers follow their actual sharing scope. A project's managed tool state may retain confidential copies elsewhere; identify and protect those locations separately rather than assuming every confidential byte lives in `private/`.

## Public references

Write public requirements, decisions and necessary rationale completely in their owning public documents. Keep confidential originals and manually maintained derivatives inside the private boundary. Installation, build, tests, documentation generation and product operation remain usable without the private tree.

An optional reference may use a neutral path such as `private/sources/context-001/notes.md#scope`, adjusted relative to the referring file, and explicitly say “private source, optional.” Use code text when a missing local target would be misleading as a link. Names and headings in the reference must also be safe to publish. Link checks exempt only explicitly marked optional private references; ordinary broken links still need repair. Public summaries, fixtures, screenshots, commit messages and release notes follow the same content boundary.

## Migration and acceptance

1. Inventory authorized materials, original/attachment relationships, destination conflicts, Git/WIP, tool registrations and references. Preserve original bytes and the source-to-destination mapping. Record any prior public tracking or publication separately; ignoring or moving a file does not remove its history.
2. Establish the outer ignore and release exclusions, then the independent inner Git and its ignore rules before moving materials. Keep a recoverable backup, migrate the selected files, repair references and make public conclusions self-contained. Inspect and commit each repository's own changes; protect the private tree during cleanup.
3. For the migration, place a temporary path checker in root `tmp/<migration>/`. Check the public final index/tree and actual release manifests for `private` or `private/` entries, including mode `160000` gitlinks; allow removals that leave no private entries in the final tree. Recreate the checker if temporary cleanup removes it before acceptance. It checks paths, not secret content.
4. Verify a nonconfidential probe is ignored publicly, both Git roots/storage/indexes/remotes are separate, originals and attachments remain recoverable, public references are optional, and the relevant public workflow works without the private tree. Exercise rejection of an accidentally staged path/gitlink and packaged path in a disposable fixture. Record the results, remaining historical exposure and backup entry point; then remove the temporary checker and its calls. Retain the layout and normal commit/release review, with no permanent hook, global Git setting or CI gate from this migration.

History rewriting has its own scope and authorization. Acceptance covers the checked materials and workflows; it does not establish that an entire publication history contains no secrets.

## Sources

- [Git ignore rules](https://git-scm.com/docs/gitignore) apply to untracked paths; already tracked files need explicit handling.
- [Git initialization](https://git-scm.com/docs/git-init) describes repository storage and initialization; verify the effective storage when creating the independent repository.
- [GitHub sensitive-data removal](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) explains the coordination and consequences of removing published history.
