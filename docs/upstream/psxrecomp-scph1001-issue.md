**Title:** SCPH-1001 LLE boot: FAIL-FAST in the CD-ROM driver at the PlayStation logo; 83 emitter "cross-function target" holes need seeds

### Summary
With the retail SCPH-1001 BIOS (LLE, real intro), the Sony intro plays and the PlayStation licence screen appears. Then the runtime hits:

```
FATAL: FAIL-FAST unknown dispatch: addr=0xBFC04F68 phys=0x1FC04F68 ra=0x00000E10 a0=0x1F801800 a1=0x1F801803
```

At that point the picture and audio freeze. `0xBFC04F68` is one of the targets `psxrecomp-bios` already warns about at generation time:

```
psxrecomp-bios: WARNING: cross-function target 0xBFC04F68 (parent guess 0x1FC04DEC) is in no emitted function — dispatching it at runtime will fail
```

The first `psxrecomp-bios` pass prints 79 of these warnings. Adding each one as a seed exposes 4 more. After two passes there are none left, and the BIOS boots through the intro into the game (Wipeout XL).

### Environment
- psxrecomp `8d56cf65`. Reproduced on the pinned framework with a downstream project's patch applied (Wipeout2K97XL). The unpatched framework behaves the same way: no CD-ROM command completes, and it never gets past the licence screen.
- Windows 11 x64; cmake-clang-v1 1.0.14 (clang 22.1.8)
- BIOS: SCPH-1001, 524288 bytes, CRC32 `37157331`, MD5 `924e392ed05558ffdb115408c263dccf`
- Banner: `bios_backend=LLE (recompiled BIOS)  bios_boot=LLE (real intro)  image=SCPH-1001`

### Fix applied locally
I appended these addresses to `recompiler/seeds/phase2_ghidra_seeds.json`, with labels `xfn_gap_<addr>`. I then re-ran `psxrecomp-bios --config bios/SCPH1001.toml` until it printed no more cross-function warnings.
- Before: emitted=1314, 79 cross-function warnings, FAIL-FAST at boot.
- After: emitted=1408, 0 warnings, boots into the game.

Pass 1 (79):
```
BFC04F58 BFC04F68 BFC04F78 BFC04F88 BFC0B7F4 BFC0BAA0 BFC0B954 BFC0BA38 BFC0BA44 BFC0D534
BFC0D54C BFC0D540 BFC11598 BFC115AC BFC14DC4 BFC14DF8 BFC14E98 BFC14ED4 BFC14F2C BFC14F88
BFC14FCC BFC14FFC BFC15038 BFC162B8 BFC16370 BFC16428 BFC1A67C BFC1A68C BFC1A69C BFC1A6AC
BFC1A6BC BFC1A6CC BFC1ACC4 BFC1ACCC BFC1ACD4 BFC1BE24 BFC1BE98 BFC1BEC0 BFC1BE88 BFC1D000
BFC1D244 BFC1D628 BFC1D824 BFC1E2E0 BFC1E398 BFC1E344 BFC1E384 BFC1E2D0 BFC1E2B8 BFC1E31C
BFC1E32C BFC1E260 BFC1E28C BFC1E218 BFC1E358 BFC1E374 BFC1E308 BFC1E48C BFC1E568 BFC1E538
BFC1E450 BFC1E47C BFC1E548 BFC1E558 BFC27F10 BFC27F30 BFC27F50 BFC27F70 BFC27F90 BFC2AE18
BFC2AED0 BFC2AF88 BFC34DF0 BFC34DC8 BFC36DA8 BFC4054C BFC40564 BFC4057C BFC40594
```
Pass 2 (4): `BFC1E508 BFC1E4EC BFC1E518 BFC1E528`

Most of these look like jump-table case targets that the function walk does not reach.

### Suggestion
The emitter already detects every one of these at build time. You could either fail the BIOS build on a non-empty set, or have discovery iterate to closure automatically. Either way, a retail BIOS would no longer build "OK" and then FAIL-FAST at the licence screen.

### Separate, smaller issue
Retail SCPH-1001 contains COP1 instructions at `0xBFC0233C` (function `0xBFC02324`, a number parser). Upstream's emitter warns and skips that function. A stricter downstream gate made this a hard failure, so it may be worth explicitly allowing COP1-only functions as skipped fatal stubs.
