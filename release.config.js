// release.config.js
const branch = process.env.COMMIT_BRANCH;

const DEFAULT_BRANCH = "main";

module.exports = {
  branches: [DEFAULT_BRANCH, { name: "*", prerelease: true }],
  plugins: [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    [
      "@semantic-release/exec",
      {
        verifyReleaseCmd: "./bump-version.sh v${nextRelease.version}",
      },
    ],
    branch === DEFAULT_BRANCH && [
      "@semantic-release/changelog",
      {
        changelogFile: "CHANGELOG.md",
      },
    ],
    branch === DEFAULT_BRANCH && "@semantic-release/git",
  ].filter(Boolean),
};
