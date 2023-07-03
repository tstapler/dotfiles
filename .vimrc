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

"Enable mouse usage for scrolling and resizing splits
set mouse+=a

" " Vim Only Settings {{{
"   if !has("nvim") 
"     if term =~ '^screen'
"       " tmux knows the extended mouse mode
"       set ttymouse=xterm2
"     endif
"   endif
" " End Vim Only Settings }}}

" Neovim Settings {{{
  if exists('&inccommand')
      set inccommand=nosplit
  endif
" End Neovim Settings }}}

if has("unix")
  if executable('zsh')
    let g:shell_location = exepath('zsh')
    execute 'set shell=' . shell_location
  elseif executable('bash')
    let g:shell_location = exepath('bash')
    execute 'set shell=' . shell_location
  endif
endif

"Set map leader
let mapleader=","

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

"Read buffers from disk when they change
set autoread

"The whitespace to show when calling :set list
set listchars=eol:$,tab:>-,trail:~,extends:>,precedes:<

" Enable syntax highlighting
syntax on

" Set persistent_undo for undotree
if has("persistent_undo")
  let undo_directory = expand("~/.undodir/")
  execute "set undodir=" . undo_directory
  set undofile
endif

if filereadable(expand("~/.vim/spell/tylerwords.utf-8.add"))
  " let g:custom_spellfile=expand("~/.vim/spell/tylerwords.utf-8.add") 
  " execute "set spellfile=" . g:custom_spellfile
endif

" }}}

" Mappings {{{

"Cycle through Quickfix list with F3
nnoremap <F3> :cn<Enter>
nnoremap <S-F3> :cp<Enter>

" Fix inconsisent Y behavior
nnoremap Y y$

" Neovim Mappings {{{
  if has("nvim")
    if executable('zsh')
      nnoremap <F7> :new term://zsh<Enter>
    elseif executable('bash')
      nnoremap <F7> :new term://bash<Enter>
    elseif executable('powershell')
      nnoremap <F7> :new term://powershell<Enter>
    endif
  endif
" End Neovim Mappings }}}
" }}}

" Local vimscript files
if isdirectory(expand("~/.vim/local"))
  for path in split(globpath('~/.vim/local/', '*'), '\n')
    execute 'source ' . path
  endfor
endif

" Plugin Manager {{{
if filereadable(expand("~/.vimrc.dein"))
   \ && (has("nvim") || version > 703)
  source ~/.vimrc.dein
else
  colorscheme slate
endif
                                                          
" End Plugin Manager }}}                                  
                                                          
" Autocommands {{{                                        

" docker-compose filetype {{{
  augroup docker-compose
    " this one is which you're most likely to use?
    autocmd Filetype docker-compose setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab smarttab
  augroup end
" End docker-compose filetype }}}

" TypeScript filetype {{{
  au Filetype ts setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab smarttab smartindent
" End TypeScript filetype }}}
                                                          
" " gitcommit filetype {{{
" au FileType gitcommit setlocal spell
" " End gitcommit filetype }}}

" Makefile filetype {{{                                   
au FileType make setlocal noexpandtab                     
" End Makefile filetype }}}

" Python filetype {{{
au FileType python setlocal tabstop=4 shiftwidth=4 softtabstop=4 expandtab smarttab
" End Python filetype }}}

" Javascript filetype {{{
au FileType javascript setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
" End Javascript filetype }}}

" Go filetype {{{
au FileType go setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
" End Go filetype }}}

" Ruby filetype {{{
au FileType ruby setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab smartindent
" End Ruby filetype }}}

" Java filetype {{{
au FileType java setlocal tabstop=4 shiftwidth=4 softtabstop=4 expandtab
" End Java filetype {{{

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

" sh filetype {{{
au FileType sh setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab smartindent
" End sh filetype }}}
"
" haproxy filetype {{{
au FileType haproxy setlocal tabstop=4 shiftwidth=4 softtabstop=4 expandtab smartindent
" End haproxy filetype }}}

" Dart filetype {{{
augroup dart
  au!
  au FileType dart setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab smarttab
augroup END
" End Dart filetype }}}

" Markdown filetype {{{
augroup markdown
  au! FileType,BufRead,BufNewFile *.markdown set filetype=mkd spell
  au FileType,BufRead,BufNewFile *.md       set filetype=mkd spell
augroup END
" End Markdown filetype }}}

" TypeScript filetype {{{
augroup typescript
  au Filetype typescript setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab smarttab
augroup END
" End TypeScript filetype }}} 

" HTML filetype {{{
au FileType html setlocal tabstop=2 shiftwidth=2 softtabstop=2 expandtab
" End HTML filetype }}}

" }}}

" Custom Functions {{{
  function! YankBufferFilename()
    :let @+ = expand("%")
  endfunction
" End Custom Functions }}}
