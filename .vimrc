" vim:fdm=marker
"
" _____     _           ___ _             _         _           _
"|_   _|  _| |___ _ _  / __| |_ __ _ _ __| |___ _ _( )___  __ _(_)_ __  _ _ __
"  | || || | / -_) '_| \__ \  _/ _` | '_ \ / -_) '_|/(_-<  \ V / | '  \| '_/ _|
"  |_| \_, |_\___|_|   |___/\__\__,_| .__/_\___|_|   /__/ (_)_/|_|_|_|_|_| \__|
"      |__/                         |_|
"

" Options {{{
"Vim not vi
if &compatible
  set nocompatible               " Be iMproved
endif

set t_Co=256

"Change the shell to vanilla to support NeoBundle
set shell=/bin/bash

"Enable mouse usage for scrolling and resizing splits
set mouse+=a

if !has("nvim") && &term =~ '^screen'
  " tmux knows the extended mouse mode
  set ttymouse=xterm2
endif

"Set map leader
let mapleader=","

"Folding options
set foldnestmax=10
set foldmethod=indent

"Help enforce 80 column code if available
if exists('colorcolumn')
  set colorcolum=80
else
  au BufWinEnter * let w:m2=matchadd('ErrorMsg', '\%>80v.\+', -1)
endif

"Show ex commands as they are being typed
set showcmd

"Use "Magic" aka regex during searches
set magic

"Set vim menu completion
set wildmenu
set wildmode=longest:list,full

"Show search results as typing
set incsearch

"Show line numbers
set number

"Show the status line even with just one window
set laststatus=2

" Enable syntax highlighting
syntax on

" Set persistent_undo for undotree
if has("persistent_undo")
  set undodir=~/.undodir/
  set undofile
endif


" Not sure why this is here -> set omnifunc+=syntaxcomplete#Complete

" }}}

" Mappings {{{

"Cycle through Quickfix list with F3
nnoremap <F3> :cn<Enter>
nnoremap <S-F3> :cp<Enter>

"Change Buffers
map <leader>n :bn<Enter>
map <leader>p :bp<Enter>
map <leader>d :bd<Enter>

if has("nvim")
  nnoremap <F7> :new term://zsh<Enter>
endif

" Fix inconsisent Y behavior
nnoremap Y y$

" }}}

" Plugin Manager {{{
if filereadable(expand("~/.vimrc.dein")) 
   \ && isdirectory(expand("~/.vim/bundle/repos")) 
   \ && (has("nvim") || version > 703)
  source ~/.vimrc.dein
else
  colorscheme slate
endif

" End Plugin Manager }}}

" Autocommands {{{

" Makefile filetype {{{
au FileType make setlocal noexpandtab
" End Makefile filetype }}}

" Python filetype {{{
au FileType python setlocal tabstop=4 shiftwidth=4 softtabstop=4 expandtab
" End Python filetype }}}

" Javascript filetype {{{
au FileType javascript setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
" End Javascript filetype }}}

" vim  filetype {{{
au FileType vim setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
" End vim  filetype }}}

" Yaml  filetype {{{
au FileType yml setlocal indentkeys-=<:> tabstop=2 softtabstop=2 expandtab
" End Yaml  filetype }}}

" fish filetype {{{
au Filetype fish compiler fish setlocal textwidth=79  foldmethod=expr
" End fish filetype }}} 

" C filetype {{{
au FileType c setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
" End C filetype }}} 

" Dart filetype {{{
augroup dart
  au FileType dart setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
augroup END
" End Dart filetype }}}

" Markdown filetype {{{
augroup markdown
  au! FileType,BufRead,BufNewFile *.markdown set filetype=mkd spell
  au! FileType,BufRead,BufNewFile *.md       set filetype=mkd spell
augroup END
" End Markdown filetype }}}

" Terminal {{{
if has('nvim')
  augroup nvim_term
      au BufEnter * if &buftype == 'terminal'  | tnoremap <C-[> <C-\><C-n> | startinsert | endif
  augroup END
endif
" End Terminal }}} 

" HTML filetype {{{
au FileType html setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
" End HTML filetype }}}

" }}}

" Reload Config On Save {{{
augroup myvimrc
  au BufWritePost .vimrc,_vimrc,vimrc,.vimrc.dein,.gvimrc,_gvimrc,gvimrc so $MYVIMRC |
        \ if has('gui_running') |
        \ so $MYGVIMRC |
        \ endif
augroup END

" End Reload Config On Save }}} 
