# The tags of the test builds of the branch $BRANCH names, from a page of releases. A test
# build's notes hold the line "test-build-branch: <branch>"; the whole line must match, so that
# one branch's name being the start of another's does not select the other's builds. $TAG, when
# set, names the test build being published, which is never selected, not even as the draft an
# interrupted upload left behind.
.[]
| select(.prerelease)
| select(.tag_name != env.TAG)
| select(
    (.body // "")
    | split("\n")
    | map(rtrimstr("\r"))
    | any(. == ("test-build-branch: " + env.BRANCH))
  )
| .tag_name
