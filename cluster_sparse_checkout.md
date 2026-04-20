# Cluster Sparse Checkout Guide

This short guide shows how to keep only the currently needed assignment folder on LCC3 in order to save disk space.

## Initial Setup on the Cluster

Clone the repository in a space-saving way:

```bash
git clone --filter=blob:none https://github.com/mayakrumholz/ps_parprog_2026.git ps_parprog_2026
cd ps_parprog_2026
git sparse-checkout init --cone
git sparse-checkout set 05
```


## Switch to Another Assignment Later

If you need a different week later, stay in the repository and run for example:

```bash
git pull
git sparse-checkout set 06
```

or for assignment 04:

```bash
git pull
git sparse-checkout set 04
```

This updates the repository and checks out only the selected folder.

## Keep Multiple Folders

If you need more than one assignment at the same time, list all required folders:

```bash
git sparse-checkout set 04 05
```

## Check What Is Currently Active

```bash
git sparse-checkout list
ls
```

## Recommended Workflow Each Week

1. Log in to LCC3.
2. Go to the repository directory.
3. Run `git pull`.
4. Run `git sparse-checkout set <assignment-folder>`.
5. Work only in that folder and remove large result files when they are no longer needed.

Example:

```bash
cd ~/ps_parprog_2026
git pull
git sparse-checkout set 05
cd 05
```

## If Disk Quota Is Still Tight

The source code usually needs little space. Large files are more often the problem:

- result folders
- images
- log files
- compiled binaries

Useful cleanup commands:

```bash
make clean
du -sh ./*
rm -rf results
```
