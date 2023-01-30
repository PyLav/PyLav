# Changelog

## v1.3.4 (30/01/2023)
- [remove unnecessary async methods](https://github.com/Drapersniper/PyLav/commit/5a674424ac83783b5df9f2abaf8c61bf9f11b5f3) - @Drapersniper
- [KeyError fix for when new stations are added to RadioBrowser and cache is not up to date.](https://github.com/Drapersniper/PyLav/commit/f4e26a99eea375347d6d11abe1804b33846edcd5) - @Drapersniper

---

## v1.3.3 (29/01/2023)
- [Add caching to the Radio transformers, improve transformers performance](https://github.com/Drapersniper/PyLav/commit/15383ca5189ebdeeddcb85377f28eef956198abd) - @Drapersniper

---

## v1.3.2 (28/01/2023)
- [Fix incorrect boolean in Client.managed_node_is_enabled](https://github.com/Drapersniper/PyLav/commit/cda5e6cff92acbb1a531a651160a7a2547767ebd) - @Drapersniper
- [Disable Managed node if running inside a container](https://github.com/Drapersniper/PyLav/commit/e374c937a51591a5bfb552993041564cb71db668) - @Drapersniper

---

## v1.3.1 (28/01/2023)
- [Add a version bump as part of the release logic](https://github.com/Drapersniper/PyLav/commit/fde01a1fefc393e0263c0423a5f768485f037885) - @Drapersniper
- [Dependency update](https://github.com/Drapersniper/PyLav/commit/a51a5897baff810d29f9ccc1714e4c816d6d7420) - @Drapersniper
- [pre-commit updates](https://github.com/Drapersniper/PyLav/commit/57eaa6eac2a07e873b016c58eec8f1b8636f77ae) - @Drapersniper
- [Bump crowdin/github-action from 1.5.3 to 1.6.0 (#169)](https://github.com/Drapersniper/PyLav/commit/17265241a4fe7dea5b68ab1e9ef1f31a36a46c84) - @dependabot[bot]
- [formatting](https://github.com/Drapersniper/PyLav/commit/b61f421c212f42bf451be8623f55a9aacc36c0d4) - @Drapersniper
- [Update documentation](https://github.com/Drapersniper/PyLav/commit/e923f6944225f8fda72b9e636af66a57761395ed) - @Drapersniper

---

## v1.3.0 (23/01/2023)
- [enhancements to reduce duplicate work on track conversions](https://github.com/Drapersniper/PyLav/commit/03ea4608d6e582c0fdf68d61aa2a01ef36d78cd0) - @Drapersniper
- [Stricter type definitions aligned with Lavalink V4](https://github.com/Drapersniper/PyLav/commit/dc26c0d237480871894aa1651e0856bd98a2309f) - @Drapersniper
- [Fix a startup issue that could happen on an OS change](https://github.com/Drapersniper/PyLav/commit/7a9a1878ced6b3df44a297b09d19f82e0b6643ab) - @Drapersniper
- [pre-commit update](https://github.com/Drapersniper/PyLav/commit/96a8160d2c49bda82ce908d7460b2a9cec8f79ee) - @Drapersniper
- [fix docker-compose.yml envvar](https://github.com/Drapersniper/PyLav/commit/e2cab308f0b55b01349482827e101aff6a1084e3) - @Drapersniper
- [update docker-compose.yml with new red image](https://github.com/Drapersniper/PyLav/commit/a80e543a11e4df1b89d2a6c9cfe9b9778ad7337e) - @Drapersniper
- [Update Docker image to my fork of Phase](https://github.com/Drapersniper/PyLav/commit/f395f55d0020224f498b2e808bc6e6f114ad1e14) - @Drapersniper

---

## v1.2.7 (22/01/2023)
- [Fix incorrect assignement due to walrus](https://github.com/Drapersniper/PyLav/commit/44b55d8456743e3be0b6f6dbd050c20c67fb178d) - @Drapersniper

---

## v1.2.6 (22/01/2023)
- [fix incorrect assignment](https://github.com/Drapersniper/PyLav/commit/3529b64ddc7b0a5a6de70c25ac453215e9766107) - @Drapersniper
- [undo accidental deletion](https://github.com/Drapersniper/PyLav/commit/0c5e325a5f34aefbab08c8aa58aa3cb61c63b27c) - @Drapersniper
- [Introduce end-of-line normalization](https://github.com/Drapersniper/PyLav/commit/a8a08a6ea6c5522cbdc67db79303c894c81d63ab) - @Drapersniper
- [if PYLAV__DATA_FOLDER is defined, and PYLAV__YAML_CONFIG is not specified, create the pylav.yaml file inside PYLAV__DATA_FOLDER](https://github.com/Drapersniper/PyLav/commit/3b58dd42ce1a80a667f31f38e4120b319f83b982) - @Drapersniper
- [update docker compose to use githubs image repo](https://github.com/Drapersniper/PyLav/commit/dccecf9de9b7f72c2372d09657780fe576224b2b) - @Drapersniper
- [Override localtracks folder as part of migrations if the envvar is explicitly set](https://github.com/Drapersniper/PyLav/commit/896048c7a0989764b0aadcbb0269a7f4e4207c6b) - @Drapersniper

---

## v1.2.5 (22/01/2023)
- [fix incorrect URL import](https://github.com/Drapersniper/PyLav/commit/69893a4269e1d84c7af4b580416c3b20ff489e02) - @Drapersniper
- [Use `yarl` which is a dep of aiohttp](https://github.com/Drapersniper/PyLav/commit/bd5ce779c77fcdb2a7c14f0b21320561ff90ec2d) - @Drapersniper
- [Fix RadioBrowser resolution and simplify logic](https://github.com/Drapersniper/PyLav/commit/f382e7356af321cc7ab1bfe3d9b1051447f94709) - @Drapersniper
- [fix NameError: name '__load_origin' is not defined](https://github.com/Drapersniper/PyLav/commit/449aadc52b924822b3631262687ee6bc066b28cd) - @Drapersniper

---

## v1.2.4 (21/01/2023)
- [fix AttributeError: 'Red' object has no attribute 'dispatch_event'](https://github.com/Drapersniper/PyLav/commit/acb26eeda14573ede7649044ca6e08c83f221abf) - @Drapersniper
- [add home helper code to identify origins](https://github.com/Drapersniper/PyLav/commit/f73b2d724d1db0cd125e21667e0c8f8e0cddf661) - @Drapersniper
- [Bump dependencies](https://github.com/Drapersniper/PyLav/commit/18c6c7bd4568f20d5059a8b2178c9af0e29f674b) - @Drapersniper
- [fix incorrect doc strings](https://github.com/Drapersniper/PyLav/commit/95245e1e6191ea8ce5e7fe71b1fe6f14668f35f8) - @Drapersniper
- [Implement a compatibility module for the json module which uses fastest json module available for any given op](https://github.com/Drapersniper/PyLav/commit/9bf08eac497bc3c2a152c1e37ac5e49512400529) - @Drapersniper

---

## v1.2.3 (21/01/2023)
- [add `PlayerAutoDisconnectedEmptyQueueEvent`  `PlayerAutoDisconnectedAloneEvent` `PlayerAutoPausedEvent` and `PlayerAutoResumedEvent` events to the player](https://github.com/Drapersniper/PyLav/commit/26e48b07448cabf25584a55810d8b75b304d2afc) - @Drapersniper
- [add `PYLAV__YAML_CONFIG` and `PYLAV__LOCAL_TRACKS_FOLDER` env vars](https://github.com/Drapersniper/PyLav/commit/2458cc2461150835b197d73625ad894771a5789c) - @Drapersniper
- [explicitly set the hostname and container_name](https://github.com/Drapersniper/PyLav/commit/ecbbfb6db28e7b8e88a9a969b958904b6f1ece36) - @Drapersniper

---

## v1.2.2 (18/01/2023)
- [properly use PYLAV__EXTERNAL_UNMANAGED_NAME](https://github.com/Drapersniper/PyLav/commit/273b5046238d5ef1e178975967f5b433fe3a2cdf) - @Drapersniper

---

## v1.2.1 (18/01/2023)
- [Remove caching from radio browser api init](https://github.com/Drapersniper/PyLav/commit/a4e870d8236204ef8387ff5bc44f6390346d84ca) - @Drapersniper

---

## v1.2.0 (18/01/2023)
- [Enforce Env Var on config stored values (Run a migration on every start up)](https://github.com/Drapersniper/PyLav/commit/0295ddeacc89f8449e7d84cd0b208bedb85c51da) - @Drapersniper
- [Add PYLAV__EXTERNAL_UNMANAGED_NAME to allow setting a name to the EnvVar node and set ENV Vars to take precedence over the file values](https://github.com/Drapersniper/PyLav/commit/66643bb714fc67f6a0e4bc7cad4ecb34e02d624a) - @Drapersniper
- [update docker-compose.yml](https://github.com/Drapersniper/PyLav/commit/650e7308758858c8139eb8ef0ffbb96a41e881d8) - @Drapersniper

---

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
