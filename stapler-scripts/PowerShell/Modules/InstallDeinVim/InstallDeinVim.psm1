# Installer for dein.vim
Function Install-DeinVim
{
    Param(
    [Parameter(Mandatory=$true)]
    [string]$plugin_dir
    )

     if ((Get-Command "git" -ErrorAction SilentlyContinue) -eq $null) 
    { 
        Write-Host "Unable to find git in your PATH"
    }

    $plugin_dir = [System.IO.Path]::GetFullPath(([io.path]::Combine((pwd), $plugin_dir)))

    $install_dir = "$plugin_dir\repos\github.com\Shougo\dein.vim"
    
    if(Test-Path -Path $install_dir) {
        Write-Host "Install directory already exists"
        Return
    }

    Write-Host "Begin fetching dein..."
    if(!(Test-Path $plugin_dir)) {
        New-Item -Path "$plugin_dir" | Out-Null
    }

    git clone https://github.com/Shougo/dein.vim "$install_dir"

    Write-Host "Done."

    # write initial setting for .vimrc
Write-Host "Please add the following settings for dein to the top of your vimrc (Vim) or init.vim (NeoVim) file:"
$sample_config = @"
    "dein Scripts-----------------------------
    if &compatible
      set nocompatible               " Be iMproved
    endif
    
    " Required:
    set runtimepath+=$INSTALL_DIR
    
    " Required:
    if dein#load_state('$PLUGIN_DIR')
      call dein#begin('$PLUGIN_DIR')
    
      " Let dein manage dein
      " Required:
      call dein#add('$INSTALL_DIR')
    
      " Add or remove your plugins here:
      call dein#add('Shougo/neosnippet.vim')
      call dein#add('Shougo/neosnippet-snippets')
    
      " You can specify revision/branch/tag.
      call dein#add('Shougo/vimshell', { 'rev': '3787e5' })
    
      " Required:
      call dein#end()
      call dein#save_state()
    endif
    
    " Required:
    filetype plugin indent on
    syntax enable
    
    " If you want to install not installed plugins on startup.
    "if dein#check_install()
    "  call dein#install()
    "endif
    
    "End dein Scripts-------------------------
"@

Write-Host $sample_config

Write-Host "Done."

Write-Host "Complete setup dein!"

}

Export-ModuleMember -function Install-DeinVim
