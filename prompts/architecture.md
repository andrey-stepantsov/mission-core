# SRL Repository Architecture Guide

## 1. The "Split-Brain" Reality
This repository is a Monorepo with two distinct execution environments. You must know which one you are in.

### Zone A: Application Layer (Root)
* **Path:** `/srl-repo/app1`
* **Environment:** Dockerized Builder (via `./rmk`)
* **Compiler:** Clang++ (Standard Linux)
* **Build Trigger:** `ddd-wait` (Target: `dev`)

### Zone B: ASIC SDK (Subtree)
* **Path:** `/srl-repo/asic/sdk1`
* **Environment:** Host Native (via `./lmk`)
* **Compiler:** GCC 11 (RedHat Devtoolset via Host Daemon)
* **Critical:** This environment has access to out-of-tree headers that the container DOES NOT see directly. You rely on `ctx` to weave them.
* **Build Trigger:** `ddd-wait` (Target: `dev`)

## 2. Your Toolkit
* **ddd-wait:** Triggers the build for your current zone. The daemon handles the complexity.
* **ctx:** Generates a Context Map. Run this if you are lost or need to see header definitions.
