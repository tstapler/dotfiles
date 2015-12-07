"
"Tyler Stapler's vimrc file
"
"author: Tyler Stapler
"

set t_Co=256

"Change the shell from fish to support NeoBundle
set shell=/bin/sh

"Set map leader
let mapleader=","

"Folding options
set foldnestmax=10
set foldmethod=indent

"Use the space bar to open/close folds
nnoremap <space> za

"Cycle through Quickfix list with F3 
map <F3> :cn<Enter>
map <S-F3> :cp<Enter>

"Change Buffers
map <leader>n :bn<Enter>
map <leader>p :bp<Enter>
map <leader>d :bd<Enter>

"When editing python F9 to drop to python shell
nnoremap <buffer> <F9> :exec '!python' shellescape(@%, 1)<cr>

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
set wildoptions

set nocompatible

"Enable YouCompleteMe"
filetype plugin indent on

set omnifunc=syntaxcomplete#Complete

"Auto Refresh Config if updated
augroup myvimrc
	au!
	au BufWritePost .vimrc,_vimrc,vimrc,.gvimrc,_gvimrc,gvimrc,.vimrc.local,.vimrc.bundle.local so $MYVIMRC | if has('gui_running') | so $MYGVIMRC | endif
augroup END


"Note: Skip initialization for vim-tiny or vim-small.
if 0 | endif

if has('vim_starting')
	if &compatible
		set nocompatible               " Be iMproved
	endif

	" Required:
	set runtimepath+=~/.vim/bundle/neobundle.vim/
endif

" Required:
call neobundle#begin(expand('~/.vim/bundle/'))

" Let NeoBundle manage NeoBundle
" Required:
NeoBundleFetch 'Shougo/neobundle.vim'

" My Bundles here:
" Refer to |:NeoBundle-examples|.
" Note: You don't set neobundle setting in
".gvimrc!
"
NeoBundle 'Chiel92/vim-autoformat'
NeoBundle 'Shougo/neocomplete.vim.git'
NeoBundle 'Shougo/neosnippet'
NeoBundle 'Shougo/neosnippet-snippets'
NeoBundle 'Shougo/unite.vim'
NeoBundle 'bling/vim-airline'
NeoBundle 'briancollins/vim-jst'
NeoBundle 'elzr/vim-json'
NeoBundle 'godlygeek/tabular'
NeoBundle 'groenewege/vim-less'
NeoBundle 'mattn/gist-vim'
NeoBundle 'tpope/vim-fugitive'
NeoBundle 'tpope/vim-surround'
NeoBundle 'flazz/vim-colorschemes'
NeoBundle 'Chiel92/vim-autoformat'
NeoBundle 'dansomething/vim-eclim'
NeoBundle 'rking/ag.vim'
NeoBundle 'tapichu/asm2d-vim'
NeoBundle 'Shougo/vimproc.vim', {
\ 'build' : {
\     'windows' : 'tools\\update-dll-mingw',
\     'cygwin' : 'make -f make_cygwin.mak',
\     'mac' : 'make',
\     'linux' : 'make',
\     'unix' : 'gmake',
\    },
\ }
"TODO: Add Vimshell
"TODO: Add eclim

call neobundle#end()

" Required:
filetype plugin indent on

" If there are uninstalled bundles found on
"startup,
" this will conveniently prompt you to
"install them.
NeoBundleCheck


"Unite Vim
call unite#filters#matcher_default#use(['matcher_fuzzy'])
call unite#filters#sorter_default#use(['sorter_rank'])
call unite#custom#source('file,file/new,buffer,file_rec,line', 'matchers', 'matcher_fuzzy')

"Fuzzy Search like Ctrl-P
nnoremap <C-p> :Unite -start-insert tab file_rec/async<cr>

let g:unite_source_history_yank_enable=1
let g:unite_enable_start_insert=1
nnoremap <space>y :Unite history/yank<cr>

"Neocomplete config
let g:neocomplete#enable_at_startup = 1
let g:neocomplete#enable_auto_select = 0
let g:neocomplcache_enable_at_startup = 0

"Airline Config
let g:airline#extensions#tabline#enabled = 1
let g:airline#extensions#virtualenv#enabled = 1

  if !exists('g:airline_symbols')
    let g:airline_symbols = {}
  endif

  let g:airline_left_sep = '▶'
  let g:airline_right_sep = '«'

colorscheme badwolf
let g:airline_theme = 'badwolf'
