# Tyler Stapler's Dotfiles

These are the configuration for various machines I own. I make every attempt to do things in a cross platform manner when possible.

My primary machines run Manjaro Linux, and Ubuntu Linux. Typically, my Work computers are Macs. There are some bits to make the original Windows Subsystem for Linux work because I used Windows briefly at Work.

## Getting Started

I install my dotfiles to a new machine by using [this script](https://github.com/tstapler/stapler-scripts/blob/master/bootstrap-dotfiles.sh). It clones this repo, and symlinks my dotfiles to my home directory using [cfgcaddy](https://github.com/tstapler/cfgcaddy) a tool I wrote.

You can use alternatives such as [GNU Stow](https://www.gnu.org/software/stow/) or [yadm](https://yadm.io/docs/overview) which have more users and likely less bugs 😉.

The key idea is that you should keep your dotfiles in a git repo in somewhere like `$HOME/dotfiles` and then symlink them to your `$HOME` directory for them to be read by other tools.

Once you have that system setup, you can copy pieces of my configuration piecemeal. I don't recommend copying everything directly. This repo has grown pretty organically over the years so it contains a lot of configuration you may not 

## Features

### zsh

I a pretty comprehensive [ZSH configuration](./.zshrc)

I use [zplug](https://github.com/zplug/zplug) as my package manager, you can find the packages in [.zplug_packages.zsh](./.zplug_packages.zsh). It is responsible for installing zsh packages as well as a few binaries.

The directory [.shell](./shell) contains several scripts that are sourced in the [`.zshrc`](./.zshrc), their names should be fairly self explanatory.

### Vim (Neovim)

I'm a heavy Vim user, so I have configuration for [Intellij's vim plugin](./.ideavimrc) as well as [actual Vim](./.vimrc) split across a few different files

### Language Installation via asdf

I am a polyglot when it comes to programming languages so I use [asdf](https://github.com/asdf-vm/asdf) to manage installing different languages and versions across my machines in a consistant way.

[.tool-versions](./tool-versions) sets the global language version used across the system.

I have some configuration for installing each of the language specific plugins in the file [.shell/languages.sh](.shell/languages.sh).
