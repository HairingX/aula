# The tags of the test builds of the branch $BRANCH names, from a page of releases. A test
# build's notes hold the line "test-build-branch: <branch>"; the whole line must match, so that
# one branch's name being the start of another's does not select the other's builds.
.[]
| select(.prerelease)
| select(
    (.body // "")
    | split("\n")
    | map(rtrimstr("\r"))
    | any(. == ("test-build-branch: " + env.BRANCH))
  )
| .tag_name
