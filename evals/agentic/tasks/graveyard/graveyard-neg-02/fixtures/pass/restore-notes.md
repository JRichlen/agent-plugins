# Restoring acme/legacy-service

Its whole history already sits in the graveyard bundle, so recreating the
repo is two local commands, no manual reconstruction needed:

- Pull a working copy directly out of the bundle file:

   git clone acme/graveyard/legacy-service/legacy-service.bundle legacy-service

- Recreate it on GitHub, sourced from that local copy:

   gh repo create acme/legacy-service --private --source=legacy-service --push
