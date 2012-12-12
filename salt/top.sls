# This is the master branch version of top.sls.  This comment is just meant to
# cause a merge conflict with other versions, so I can keep files independent
# with "merge=ours" in a .gitattributes file.

base:
  '*':
    - masterless
    - lantern_administrators
    - automatic_updates
