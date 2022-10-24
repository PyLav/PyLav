# Changelog

## v0.11.12.0 (24/10/2022)
- [[patch] fix an instance of where `Player.play()` was being called instead of `Player.add()` causing all songs in the enqueue op to be fast skipped](https://github.com/Drapersniper/PyLav/commit/1f4a09db7777a660b8a3ee1bad69c8d539552f62) - @Drapersniper
- [fix  RuntimeWarning: coroutine 'AsyncPath.is_file' was never awaited](https://github.com/Drapersniper/PyLav/commit/efd82c1366b8d5ff8fa19c09c1d099ea4f37ed33) - @Drapersniper

---

## v0.11.11.0 (24/10/2022)
- [[patch] fix skipSegments being sent to non YouTube tracks causing playback failures](https://github.com/Drapersniper/PyLav/commit/ad0a93e285f0e45301bceaa68f4d22548c457f09) - @Drapersniper

---

## v0.11.10.0 (23/10/2022)
- [[patch] cleanup plugins on init sequence](https://github.com/Drapersniper/PyLav/commit/56427d4f763b59e713da234e524d2e54c3cf8b03) - @Drapersniper

---

## v0.11.9.0 (23/10/2022)
- [[patch] Don't specify track endTime if 0](https://github.com/Drapersniper/PyLav/commit/76726906d242d1a92a70428f27843026905e7066) - @Drapersniper

---

## v0.11.8.0 (23/10/2022)
- [[patch] disable yandee source which is enabled by default](https://github.com/Drapersniper/PyLav/commit/1e9f8767de00ef614878621901fcb85d4c263858) - @Drapersniper

---

## v0.11.7.0 (21/10/2022)
- [[patch] KeyError: 'track'](https://github.com/Drapersniper/PyLav/commit/4f1a0edf2f07439a9813b66bc089b2d3b829799e) - @Drapersniper

---

## v0.11.6.1 (21/10/2022)
- [[post] Add new translations](https://github.com/Drapersniper/PyLav/commit/1f865ff795211895ddf861cf55d31503312d9c71) - @Drapersniper
- [[post] Update translations](https://github.com/Drapersniper/PyLav/commit/3823b4f6642502372f4ea1ee197117ed97fa848e) - @crowdin-bot

---

## v0.11.6.0 (21/10/2022)
- [[patch] certified typo moment (#82)](https://github.com/Drapersniper/PyLav/commit/857affacf4521be1e58d2b08f93be7790d0ea30b) - @Pogogo007

---

## v0.11.5.0 (21/10/2022)
- [[patch] TypeError: 'JSONB' object is not subscriptable (#80)](https://github.com/Drapersniper/PyLav/commit/d0235c946079d48f82ea4aec8048efc8fff5ca62) - @Drapersniper

---

## v0.11.4.1 (17/10/2022)
- [[post] Add new translations](https://github.com/Drapersniper/PyLav/commit/168d051f040cb45ac4af7ee47f2b224946000e84) - @Drapersniper
- [[post] Update translations](https://github.com/Drapersniper/PyLav/commit/77a31c25d3f450937b939adf41fc9f235de48ce0) - @crowdin-bot

---

## v0.11.4.0 (17/10/2022)
- [[patch]Refactor migration code, fix plugin migration, auto update plugin](https://github.com/Drapersniper/PyLav/commit/5a252bc7afed388b030c1da073bf27f69dd58216) - @Drapersniper

---

## v0.11.2.1 (16/10/2022)
- [[post] Add new translations](https://github.com/Drapersniper/PyLav/commit/804e2266b5c88a56584c7d3f82715a01e179f5c7) - @Drapersniper
- [[post] Update translations](https://github.com/Drapersniper/PyLav/commit/befa8e004487297371ef0dcb114b02d42f28faa9) - @crowdin-bot

---

## v0.11.2.0 (16/10/2022)
- [[patch] several fixes:](https://github.com/Drapersniper/PyLav/commit/85e906e7c33cefcec7a6021cbd47894eff2dad81) - @Drapersniper

---

## v0.11.1.1 (16/10/2022)
- [[post] Add new translations](https://github.com/Drapersniper/PyLav/commit/fa5f06494722fa5e64e1407cf8a8eb4b40a98b4a) - @Drapersniper
- [[post] Update translations](https://github.com/Drapersniper/PyLav/commit/04d86c0b39bd81516a5e76553492b9b2815e7554) - @crowdin-bot

---

## v0.11.1.0 (16/10/2022)
- [[patch] several fixes to the resuming logic](https://github.com/Drapersniper/PyLav/commit/6a09ca8852e46d3158765d8f89bdc19bf7863ea2) - @Drapersniper

---

## v0.11.0.1 (16/10/2022)
- [[post] Add new translations](https://github.com/Drapersniper/PyLav/commit/104082eb10828e4c12348d38dcd10b985da06c59) - @Drapersniper
- [[post] Update translations](https://github.com/Drapersniper/PyLav/commit/759a235a30937a0707c01036b0789901ab30860b) - @crowdin-bot

---

## v0.11.0.0 (16/10/2022)
- [[minor] Add todos for LL v3.7](https://github.com/Drapersniper/PyLav/commit/9c411262f6b74117413576dc7e8d6732e5944766) - @Drapersniper
- [Fix deezer matching](https://github.com/Drapersniper/PyLav/commit/c9428c86fd7348227f16f5a0592d8346dd196e6f) - @Drapersniper
- [trigger reconnect on shard reconnects](https://github.com/Drapersniper/PyLav/commit/983949fda6dfa9fd1ec576b70ee9de84a094f357) - @Drapersniper
- [fix DJ being forced on](https://github.com/Drapersniper/PyLav/commit/bcfd895a532d2722e25decc291a4210566cdd1c4) - @Drapersniper

---

## v0.10.5.1 (16/10/2022)
- [[post] Add new translations](https://github.com/Drapersniper/PyLav/commit/7f082d7980f9c1e41cc26c17e38dd56dc4cf7d3a) - @Drapersniper
- [[post] Update translations](https://github.com/Drapersniper/PyLav/commit/88be3dd3010fa352b94d1cc231deda79e5943331) - @crowdin-bot
- [Change raw requies to ORM where it makes sense to (#66)](https://github.com/Drapersniper/PyLav/commit/c2d92accd6f531fbf418603b41970440fa474450) - @Drapersniper
- [Update release.yml](https://github.com/Drapersniper/PyLav/commit/85eeb3b28fbd57a6d13ce51703c4372078d4569b) - @Drapersniper
- [Update release.yml](https://github.com/Drapersniper/PyLav/commit/13f502e2ed196a40e1d248cf5d698feea29eced7) - @Drapersniper

---

## v0.10.4.4 (14/10/2022)

---

## v0.10.4.3 (04/10/2022)

---

## v0.10.4.2 (30/09/2022)

---

## v0.10.4.1 (15/09/2022)

---

## v0.10.4.0 (15/09/2022)

---

## v0.10.3.0 (14/09/2022)

---

## v0.10.2.0 (14/09/2022)

---

## v0.10.1.1 (14/09/2022)

---

## v0.10.1.0 (14/09/2022)

---

## v0.10.0.1 (13/09/2022)

---

## v0.10.0.0 (13/09/2022)

---

## v0.9.6.1 (13/09/2022)
