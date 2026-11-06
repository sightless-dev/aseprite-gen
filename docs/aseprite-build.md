# Building Aseprite on Windows

Run `powershell -ExecutionPolicy Bypass -File scripts/build-aseprite.ps1` from the repository. The script follows upstream [INSTALL.md](https://github.com/aseprite/aseprite/blob/v1.3.18.6/INSTALL.md), downloads official source and Skia archives, verifies pinned SHA-256 digests, discovers Visual Studio through `vswhere`, loads its compiler environment, then builds with CMake and Ninja. It does not install global tools or change the permanent PATH.

Prerequisites: Windows x64, Visual Studio 2022 Build Tools with Desktop development with C++, Windows SDK, and CMake/Ninja (the Visual Studio CMake component is sufficient). Python 3.11+ is used by the project, Node.js 20+ by Ruflo. The tested SDK was 10.0.26100.0; the installed MSVC toolset was 14.44.35207.

Verified build:

| Component | Pin/result |
|---|---|
| Aseprite source | `v1.3.18.6`, commit `331e898ef405d919539c03fd1675691cfa16c3a3` |
| Official source SHA-256 | `fa9dd07a0c2a5ec91a4166333296bbb9e5c237933b59875d0cfee849d2358306` |
| Skia | `m124-08a5439a6b`, Windows Release x64 |
| Skia archive SHA-256 | `5a371a4b2819bb4eb96e36cd75fa623585e1d5477e253a970302b6f2471b6934` |
| Configuration | `RelWithDebInfo`, `LAF_BACKEND=skia` |
| Version command | `Aseprite 1.3.18.6-dev` |
| Output | `.local/aseprite/build/bin/aseprite.exe` |

The `-dev` suffix is the actual compiled version string, despite building the pinned stable source archive. Preserve it in reports. `build-provenance.json` under `.local/aseprite` records tool versions, archive hashes and the built executable hash. Full configure/build logs are in `.local/aseprite/logs`.

The built binary has the GUI/Skia backend enabled. CLI, Lua creation, named layers, source reopen, image export and refinement were executed successfully. Manual GUI interaction was not tested. Set `ASEPRITE_PATH` to use a different installation; otherwise this project's local build is discovered automatically.

The source archive bundles upstream submodules. Aseprite and Skia retain their upstream terms. Binaries and third-party sources are not distributed in this repository.
