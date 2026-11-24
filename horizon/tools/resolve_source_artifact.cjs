// Select an exact successful build, never an unrelated "latest" artifact.
const fs = require("node:fs");
const crypto = require("node:crypto");

module.exports = async ({ github, context, core }) => {
  const { owner, repo } = context.repo;
  const source = JSON.parse(fs.readFileSync("horizon/source/current-main-ref.json", "utf8"));
  const raw = fs.readFileSync("horizon/source/current-main.json");
  const blob = crypto.createHash("sha1").update("blob " + raw.length + "\0").update(raw).digest("hex");
  if (blob !== source.manifest_blob) throw new Error("Local migration snapshot differs from pinned Git blob");
  for (const sha of [source.main_commit, source.synced_commit]) {
    const manifest = await github.rest.repos.getContent({ owner, repo, path: "modlist.json", ref: sha });
    if (manifest.data.sha !== blob) throw new Error("Pinned source manifest mismatch at " + sha);
    const runs = await github.paginate(github.rest.actions.listWorkflowRuns, {
      owner, repo, workflow_id: "build-alpha.yml", head_sha: sha, status: "success", per_page: 100
    });
    for (const run of runs) {
      if (run.head_sha !== sha || run.conclusion !== "success") continue;
      const artifacts = await github.paginate(github.rest.actions.listWorkflowRunArtifacts, {
        owner, repo, run_id: run.id, per_page: 100
      });
      const matches = artifacts.filter(a => a.name === source.artifact_name && a.expired === false);
      if (matches.length !== 1) continue;
      core.setOutput("run_id", String(run.id));
      core.setOutput("build_sha", sha);
      core.setOutput("artifact_name", source.artifact_name);
      core.info("Selected successful exact-source build " + run.id + " at " + sha);
      return;
    }
  }
  throw new Error("No non-expired successful build for either pinned source commit. Build the exact synced revision before retrying; never fall back to historical coverage.");
};
