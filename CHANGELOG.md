# Changelog

## v1.1.19 (18/01/2023)
- [Make Release](https://github.com/Drapersniper/PyLav/commit/9b2a1a1286636201ec5a3716d51768459afb3f4f) - @Drapersniper

---

## v1.1.18 (18/01/2023)
- [hotfix migration](https://github.com/Drapersniper/PyLav/commit/f80281b26fd21eefb9faccae984c49e137e46f4d) - @Drapersniper

---

## v1.1.17 (18/01/2023)
- [pre-commit update](https://github.com/Drapersniper/PyLav/commit/e8b5120f3fbedb51aab021ef7037e59b6478bb16) - @Drapersniper
- [Tweak LavaScr Providers to align with Topi's suggestion](https://github.com/Drapersniper/PyLav/commit/23247baad9b55badb12c5b68fe8d63d913f8d74e) - @Drapersniper

---

## v1.1.7 (15/01/2023)
- [Tweaks to special handling logic for node penalty](https://github.com/Drapersniper/PyLav/commit/1c27a95e7899a6102edfd3b0b64dc6e0176f1d25) - @Drapersniper
- [fix incorrect reference to pylav.docker.yaml](https://github.com/Drapersniper/PyLav/commit/fdbe1ec61e4005360ae2152738ec96bf238f422e) - @Drapersniper

---

## v1.1.6 (14/01/2023)
- [Add a special penalty handling for nodes to change the weighting](https://github.com/Drapersniper/PyLav/commit/44153b74658aca19d5c3d829977e00482dae8b52) - @Drapersniper
- [Update docker-compose.yml with the new lavasrc commit](https://github.com/Drapersniper/PyLav/commit/f6fda52bb1817a890e23266f160b2c2f74a253d3) - @Drapersniper
- [Disable the london node - as that has been sunset-ed for the time being](https://github.com/Drapersniper/PyLav/commit/867fc28cb15e0f3e8ce813663344bc86723c4d0b) - @Drapersniper
- [Add new Lavasrc configuration values for playlist and album limits (Applemusic built-in limit = 9K songs and Spotify = 11K songs)](https://github.com/Drapersniper/PyLav/commit/0de5c235336b61002b4af14bd455d32304ea9d2c) - @Drapersniper

---

## v1.1.5 (12/01/2023)
- [More optimizations](https://github.com/Drapersniper/PyLav/commit/240686c7c45c4fcd6d384ca8e334689f0504bd28) - @Drapersniper
- [optmization fixes](https://github.com/Drapersniper/PyLav/commit/df6aaf99105817218b3898c53efe621678f1aa75) - @Drapersniper
- [bulk process track where possible](https://github.com/Drapersniper/PyLav/commit/31e8df416507f29e8b1995191570566da4c62eb3) - @Drapersniper
- [Increase the node session timeouts](https://github.com/Drapersniper/PyLav/commit/cf0b3c9f0e762aadc2374060625f4f49e4bf9f8c) - @Drapersniper
- [pre-commit hook version update](https://github.com/Drapersniper/PyLav/commit/445817f0ff0a1e6db035dd29a2a3e5bad70d89d1) - @Drapersniper
- [increase session timeout for node](https://github.com/Drapersniper/PyLav/commit/3c9cbfe39278ec71ba4b655b2a86ea713810dbf2) - @Drapersniper

---

## v1.1.4 (09/01/2023)
- [Further start up enhancements](https://github.com/Drapersniper/PyLav/commit/1b89d276b8e3bceb9430cb0c36ad2f842391226f) - @Drapersniper

---

## v1.1.3 (09/01/2023)
- [Better track caching and references (Better performance)](https://github.com/Drapersniper/PyLav/commit/9eedaa9d17431e275431ea414a92a04c9ce58323) - @Drapersniper
- [Fix the base64 decoder](https://github.com/Drapersniper/PyLav/commit/b550a3d20b3f5cd01956da62e31c6143b0c5b5b4) - @Drapersniper
- [Used cached session for decode endpoints](https://github.com/Drapersniper/PyLav/commit/4197ad78cfa0210c6fc20f352b32ff91d642609a) - @Drapersniper
- [Fix incorrect cog name reference](https://github.com/Drapersniper/PyLav/commit/6b364195f70e664d4976813901aa5e462068b0d8) - @Drapersniper
- [fix AttributeError: 'NoneType' object has no attribute 'source'](https://github.com/Drapersniper/PyLav/commit/9fec736961094fcfd54afde511b6dcfe7a747df3) - @Drapersniper
- [precommit update](https://github.com/Drapersniper/PyLav/commit/839b097a2d8bd4817006e86ba0a3c94cb38038e4) - @Drapersniper
- [Update setup.md](https://github.com/Drapersniper/PyLav/commit/a6a576f57b598817c00d8ed4b5774db13e011bee) - @Drapersniper

---

## v1.1.2 (08/01/2023)
- [Update docker-compose.yml](https://github.com/Drapersniper/PyLav/commit/90d0b1e3919b0e1916d91b173607ec38e7d5fdb3) - @Drapersniper
- [Update .pre-commit-config.yaml](https://github.com/Drapersniper/PyLav/commit/313f111b139cc05166dc8e06fd5f42d8fcaf7729) - @Drapersniper
- [Fix possible AttributeError in QueueSource (#149)](https://github.com/Drapersniper/PyLav/commit/dd9d5518236eeba2715aaad59b92464a017f42eb) - @Kuro-Rui

---

## v1.1.1 (07/01/2023)
- [Bump actions/checkout from 3.1.0 to 3.3.0 (#145)](https://github.com/Drapersniper/PyLav/commit/5e1df240ffcff4f90cfc211dc297092936e14c68) - @dependabot[bot]
- [Add a missing positional argument in player.stop() (#148)](https://github.com/Drapersniper/PyLav/commit/21ac9dc7c22fa30efd3e3fe4a421ce9539e1af1d) - @Kuro-Rui

---

## v1.1.0 (06/01/2023)
- [Cleanup docker-compose.yml](https://github.com/Drapersniper/PyLav/commit/6a74b5b850ea5fd880da50a6578f254b0acde969) - @Drapersniper
- [Add every possible configuration option as an env var](https://github.com/Drapersniper/PyLav/commit/ca0b71a12e1c6f8b9e24460fd103b4ac80bb143d) - @Drapersniper
- [ignore unknown events rather than restarting the websocket connection](https://github.com/Drapersniper/PyLav/commit/59546915bc9ff1de2ffa2da1ff1c0423a6427ea3) - @Drapersniper
- [Fixes incorrect references to SegmentLoaded/SegmentSkipped events from the sponsorblock plugin](https://github.com/Drapersniper/PyLav/commit/d67c2eb47eb09c150db5e8166422f99823c80892) - @Drapersniper
- [Cleanup Sponsorblock changes](https://github.com/Drapersniper/PyLav/commit/c5fc1e0fba962401ae0ff286e99d6df76116440a) - @Drapersniper
- [Update Sponsorblock plugin to pre-release version with RESTAPI support](https://github.com/Drapersniper/PyLav/commit/4d32b74f4437f00cf7c0b5397da32561da36b9be) - @Drapersniper

---

## v1.0.15 (05/01/2023)
- [correct reset track position for historic tracks and enhanced query meta persistence](https://github.com/Drapersniper/PyLav/commit/c4c8f6ecc3e8a93e817569f6d95a8ed452ec3adf) - @Drapersniper
- [don't discard query metadata on rebuild (i.e Properly allow users to use link timestamp for youtube, spotify and soundcloud)](https://github.com/Drapersniper/PyLav/commit/fc28eac4825117ddae715b12ef1896830b560205) - @Drapersniper
- [Reference source regex](https://github.com/Drapersniper/PyLav/commit/f8337cd1d09842dabc6da28f3da90d95358e2a32) - @Drapersniper
- [Handle TrackNotFoundException closes #143](https://github.com/Drapersniper/PyLav/commit/f98470bc77b66ce4c8283f19c83bfdc4843d6e47) - @Drapersniper

---

## v1.0.14 (04/01/2023)
- [Make Release](https://github.com/Drapersniper/PyLav/commit/c2c8562fa79698bf76c200d69ffd9daecbe7891e) - @Drapersniper

---

## v1.0.13 (04/01/2023)
- [v1.0.13 (#140)](https://github.com/Drapersniper/PyLav/commit/770238c7cf1de68c9218a3327364bbc52dbbc100) - @Drapersniper
- [Update SETUP.md](https://github.com/Drapersniper/PyLav/commit/121cfdd1bc4aa8455a0018403c6dbafb61e7e93c) - @Drapersniper
- [Remove even more old locale folders](https://github.com/Drapersniper/PyLav/commit/ab156ad3848c454918795bb1d049363299abbbf1) - @Drapersniper
- [remove invalid locales folder](https://github.com/Drapersniper/PyLav/commit/51a6bb88bbb33d61ac3d90b6d208fcb6f96fe1e6) - @Drapersniper

---

## v1.0.12 (02/01/2023)
- [`[p]plsyncslash` should be owner only v2](https://github.com/Drapersniper/PyLav/commit/2f5c1c5d417edc4292ace9bf01e471618c0bf6f7) - @Drapersniper

---

## v1.0.11 (02/01/2023)
- [`[p]plsyncslash` should be owner only](https://github.com/Drapersniper/PyLav/commit/5690710cdabf5b6b245043c01a50f0f0cdaafbe3) - @Drapersniper
- [Remove old invalid locale folders](https://github.com/Drapersniper/PyLav/commit/9f2b28f4c7eaa589a3df20cb83274c9b67b3af7a) - @Drapersniper
- [[CI] Add automerge label to workflow prs](https://github.com/Drapersniper/PyLav/commit/7ab00839d50b6c686362fa1b37303436792eb560) - @Drapersniper

---

## v1.0.10 (02/01/2023)
- [Make sure name attribute can exist before accessing it](https://github.com/Drapersniper/PyLav/commit/037e0c4f0a93acbc7c4642e22f899bd99e7c70c0) - @Drapersniper

---

## v1.0.9 (02/01/2023)
- [default the PyLav external node to off](https://github.com/Drapersniper/PyLav/commit/7217d3bf68a385ca5c8d5f591395c29531f9eed1) - @Drapersniper

---

## v1.0.8 (02/01/2023)
- [fix to avoid the local database being constantly wiped](https://github.com/Drapersniper/PyLav/commit/dba0dcadf21c91fe1b8fa7fd2a72e60cdee5d598) - @Drapersniper
- [Remove `lava.link` bundled node permanently](https://github.com/Drapersniper/PyLav/commit/d7f201297e56f91faff0842541c8e92265bba56a) - @Drapersniper
- [make the redbot container depend on the postgres and ll-node containers](https://github.com/Drapersniper/PyLav/commit/d6ac80a1c309e0619431b01b54f43d8268bc478f) - @Drapersniper
- [Dependency update and cleanup](https://github.com/Drapersniper/PyLav/commit/7a51c40100e734aa151ea72e5751a39317fb47b6) - @Drapersniper

---

## v1.0.7 (02/01/2023)


---

## v1.0.6 (02/01/2023)
## What's Changed
* New Crowdin translations by Github Action by @Drapersniper in https://github.com/Drapersniper/PyLav/pull/132


**Full Changelog**: https://github.com/Drapersniper/PyLav/compare/v1.0.4...v1.0.6
---

## v1.0.5 (02/01/2023)
- [delete empty queries in cache](https://github.com/Drapersniper/PyLav/commit/9e70abea40b967950b7fb2129502d423697ed8cd) - @Drapersniper
- [Only return cached entry if there are tracks to be returned](https://github.com/Drapersniper/PyLav/commit/e10369fa5549217c2e8e54f0a616de1b7e93a5b4) - @Drapersniper
- [Add a note to the the setup.md](https://github.com/Drapersniper/PyLav/commit/e38ba1089c3960ac846b982b125a804fa0ea31ad) - @Drapersniper

---

## v1.0.4 (01/01/2023)
- [Add the youtube email config option](https://github.com/Drapersniper/PyLav/commit/7f98770f7ad81e73a476c82b749755e172a613cd) - @Drapersniper
- [Expose the dispatch manager attribute of pylav](https://github.com/Drapersniper/PyLav/commit/d2aecaafeb483a83f3218175d84f7264f8a73726) - @Drapersniper
- [Better documentation](https://github.com/Drapersniper/PyLav/commit/b5ee42b0552b7f362e52777e8c0fa30934738331) - @Drapersniper
- [Ignore DB connection errors on tasks](https://github.com/Drapersniper/PyLav/commit/bcc35de6beea4558e3d631a7c731b288b2c1c682) - @Drapersniper

---

## v1.0.3 (01/01/2023)
- [Add a workflow dispatch to PyLav-Cogs](https://github.com/Drapersniper/PyLav/commit/ad3b246c5d7c50eb821036ae20fbbc3bdfea6c25) - @Drapersniper
- [fix versioning](https://github.com/Drapersniper/PyLav/commit/9683e6d8702b20e24a42dc517623d8c04c10cdcf) - @Drapersniper
- [Sourcery](https://github.com/Drapersniper/PyLav/commit/9dc5bb339e1963f12a0c0860d89a98d3a4bc6f6a) - @Drapersniper

---

## v1.0.2 (01/01/2023)
- [Cleanup](https://github.com/Drapersniper/PyLav/commit/5b734b8408c159c38a09060aec991192a5f4b849) - @Drapersniper
- [Cleanup](https://github.com/Drapersniper/PyLav/commit/bfa1d4f4e2d75b28444076a0030632bccf4785e8) - @Drapersniper
- [Clarification in the SETUP.md](https://github.com/Drapersniper/PyLav/commit/950d642586a8188c07f0752e0ef9bb6d287460da) - @Drapersniper

---

## v1.0.1 (01/01/2023)
- [Properly parse applemusic and mixcloud queries](https://github.com/Drapersniper/PyLav/commit/e5beceed727b733bb497afef58fbb14ff65df5fe) - @Drapersniper
- [Fix regex for Spotify, apple music, bandcamp and soundcloud](https://github.com/Drapersniper/PyLav/commit/ee915ea302c324ca899150e197b35a5b5d918e82) - @Drapersniper
- [Some clarification of docker usage](https://github.com/Drapersniper/PyLav/commit/9810baa4807b50da70c86caee2f4ff439607e8fe) - @Drapersniper
- [Add a mention to discord to use docker container](https://github.com/Drapersniper/PyLav/commit/20de69c33fce4ada25aadf0dff408870c3981564) - @Drapersniper
- [add workflow_dispatch: to certain workflows](https://github.com/Drapersniper/PyLav/commit/ea99e761e98570fc719aa8c05202938b54e78f23) - @Drapersniper
- [Fix crowdin workflows](https://github.com/Drapersniper/PyLav/commit/706c842847a6a9e4e363c67f6698f168e454bb1e) - @Drapersniper

---

## v1.0.0 (30/12/2022)
- [fix release.yml](https://github.com/Drapersniper/PyLav/commit/08d440d79eef207a6a92b6987f394069c01befff) - @Drapersniper
- [reexport gren token](https://github.com/Drapersniper/PyLav/commit/81b453673c0171dec1c78043cf5733549fbf1311) - @Drapersniper
- [force token](https://github.com/Drapersniper/PyLav/commit/79447bd5213fa365b5bbf0bfe5a8f892cb644577) - @Drapersniper
- [reuse poetry cache on changelogs](https://github.com/Drapersniper/PyLav/commit/7d0509ad2c9e9d5611913f1b74c49d01b6dddcee) - @Drapersniper
- [don't try to publish if already existing](https://github.com/Drapersniper/PyLav/commit/cefc3e668d2c5a422f0090934f9a3c22daa4bac9) - @Drapersniper
- [Only run release on Ubuntu-latest for now](https://github.com/Drapersniper/PyLav/commit/b2ede0799801e78ad5289d43abe74c0362a72404) - @Drapersniper
- [Fixes release workflow](https://github.com/Drapersniper/PyLav/commit/7f4e87597d5fb910fb7f283c37ff21abedbaa7d7) - @Drapersniper
- [Fixes release workflow](https://github.com/Drapersniper/PyLav/commit/fa323e0d5b7c60634e337876759cf1c344720dd9) - @Drapersniper
- [1 0 0](https://github.com/Drapersniper/PyLav/commit/2b2fac3f4f3da7b790af0728292554410eda00f3) - @Drapersniper

---

## v0.11.20.0 (30/12/2022)
- [[patch] make patch release](https://github.com/Drapersniper/PyLav/commit/a04b7ca0a694e5ce43abc01400e97af981acefbb) - @Drapersniper
- [[patch] ignore unsupported lavalink releases (3.7+)](https://github.com/Drapersniper/PyLav/commit/2a236366ca4d439c60fd402c3a6b06f6d69a40c0) - @Drapersniper
- [add labeler.yml](https://github.com/Drapersniper/PyLav/commit/b73b4636b5ea5377d4ebec031c2e90cbbe1ec3e1) - @Drapersniper
- [Bump actions/dependency-review-action from 2 to 3](https://github.com/Drapersniper/PyLav/commit/e7ddb46c1ea723157b4ef38f4b4fc00b90948c8f) - @dependabot[bot]
- [Bump crowdin/github-action from 1.5.0 to 1.5.1](https://github.com/Drapersniper/PyLav/commit/012e60dd64c02d05050067e4ef96bb9c46070b66) - @dependabot[bot]
- [workflows](https://github.com/Drapersniper/PyLav/commit/b125e84e0f235fa8b0661834d91fa3ffac3455eb) - @Drapersniper

---

## v0.11.19.1 (26/11/2022)
- [[post] Add new translations](https://github.com/Drapersniper/PyLav/commit/b6a70d2af59d3593532a89e2a3af705180151f24) - @Drapersniper
- [[post] Update translations](https://github.com/Drapersniper/PyLav/commit/170d8c09d834c952c5018e517ec877a96675929c) - @crowdin-bot

---

## v0.11.19.0 (26/11/2022)
- [[patch] Properly fix  NameError: name 'tables' is not defined](https://github.com/Drapersniper/PyLav/commit/ee9521e95e40a97245dab038634101e0359b866f) - @Drapersniper
