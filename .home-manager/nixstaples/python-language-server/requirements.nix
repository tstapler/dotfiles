# generated using pypi2nix tool (version: 1.8.1)
# See more at: https://github.com/garbas/pypi2nix
#
# COMMAND:
#   pypi2nix -V 3.6 -e python-language-server[all]
#

{ pkgs ? import <nixpkgs> {}
}:

let

  inherit (pkgs) makeWrapper;
  inherit (pkgs.stdenv.lib) fix' extends inNixShell;

  pythonPackages =
  import "${toString pkgs.path}/pkgs/top-level/python-packages.nix" {
    inherit pkgs;
    inherit (pkgs) stdenv;
    python = pkgs.python36;
    # patching pip so it does not try to remove files when running nix-shell
    overrides =
      self: super: {
        bootstrapped-pip = super.bootstrapped-pip.overrideDerivation (old: {
          patchPhase = old.patchPhase + ''
            sed -i               -e "s|paths_to_remove.remove(auto_confirm)|#paths_to_remove.remove(auto_confirm)|"                -e "s|self.uninstalled = paths_to_remove|#self.uninstalled = paths_to_remove|"                  $out/${pkgs.python35.sitePackages}/pip/req/req_install.py
          '';
        });
      };
  };

  commonBuildInputs = [];
  commonDoCheck = false;

  withPackages = pkgs':
    let
      pkgs = builtins.removeAttrs pkgs' ["__unfix__"];
      interpreter = pythonPackages.buildPythonPackage {
        name = "python36-interpreter";
        buildInputs = [ makeWrapper ] ++ (builtins.attrValues pkgs);
        buildCommand = ''
          mkdir -p $out/bin
          ln -s ${pythonPackages.python.interpreter}               $out/bin/${pythonPackages.python.executable}
          for dep in ${builtins.concatStringsSep " "               (builtins.attrValues pkgs)}; do
            if [ -d "$dep/bin" ]; then
              for prog in "$dep/bin/"*; do
                if [ -f $prog ]; then
                  ln -s $prog $out/bin/`basename $prog`
                fi
              done
            fi
          done
          for prog in "$out/bin/"*; do
            wrapProgram "$prog" --prefix PYTHONPATH : "$PYTHONPATH"
          done
          pushd $out/bin
          ln -s ${pythonPackages.python.executable} python
          ln -s ${pythonPackages.python.executable}               python3
          popd
        '';
        passthru.interpreter = pythonPackages.python;
      };
    in {
      __old = pythonPackages;
      inherit interpreter;
      mkApplication = pythonPackages.buildPythonApplication;
      mkDerivation = pythonPackages.buildPythonPackage;
      packages = pkgs;
      overrideDerivation = drv: f:
        pythonPackages.buildPythonPackage (drv.drvAttrs // f drv.drvAttrs //                                            { meta = drv.meta; });
      withPackages = pkgs'':
        withPackages (pkgs // pkgs'');
    };

  python = withPackages {};

  generated = self: {

    "autopep8" = python.mkApplication {
      name = "autopep8-1.3.5";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/b7/0c/20cf0a438d5273bfd2d607ada3a7a782845ab3776c1c83c1d3baca05535e/autopep8-1.3.5.tar.gz"; sha256 = "2284d4ae2052fedb9f466c09728e30d2e231cfded5ffd7b1a20c34123fdc4ba4"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."pycodestyle"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/hhatto/autopep8";
        license = licenses.mit;
        description = "A tool that automatically formats Python code to conform to the PEP 8 style guide";
      };
    };



    "future" = python.mkApplication {
      name = "future-0.16.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/00/2b/8d082ddfed935f3608cc61140df6dcbf0edea1bc3ab52fb6c29ae3e81e85/future-0.16.0.tar.gz"; sha256 = "e39ced1ab767b5936646cedba8bcce582398233d6a627067d4c6a454c90cfedb"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://python-future.org";
        license = licenses.mit;
        description = "Clean single-source support for Python 3 and 2";
      };
    };



    "jedi" = python.mkApplication {
      name = "jedi-0.12.1";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/49/2f/cdfb8adc8cfc9fc2e5673e724d9b9098619dc1a2772cc6b8af34c6b7bef9/jedi-0.12.1.tar.gz"; sha256 = "b409ed0f6913a701ed474a614a3bb46e6953639033e31f769ca7581da5bd1ec1"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."parso"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/davidhalter/jedi";
        license = licenses.mit;
        description = "An autocompletion tool for Python that can be used for text editors.";
      };
    };



    "mccabe" = python.mkApplication {
      name = "mccabe-0.6.1";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/06/18/fa675aa501e11d6d6ca0ae73a101b2f3571a565e0f7d38e062eec18a91ee/mccabe-0.6.1.tar.gz"; sha256 = "dd8d182285a0fe56bace7f45b5e7d1a6ebcbf524e8f3bd87eb0f125271b8831f"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/pycqa/mccabe";
        license = licenses.mit;
        description = "McCabe checker, plugin for flake8";
      };
    };



    "parso" = python.mkDerivation {
      name = "parso-0.3.1";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/46/31/60de7c9cbb97cac56b193a5b61a1fd4d21df84843a570b370ec34781316b/parso-0.3.1.tar.gz"; sha256 = "35704a43a3c113cce4de228ddb39aab374b8004f4f2407d070b6a2ca784ce8a2"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/davidhalter/parso";
        license = licenses.mit;
        description = "A Python Parser";
      };
    };



    "pluggy" = python.mkDerivation {
      name = "pluggy-0.7.1";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/a1/83/ef7d976c12d67a5c7a5bc2a47f0501c926cabae9d9fcfdc26d72abc9ba15/pluggy-0.7.1.tar.gz"; sha256 = "95eb8364a4708392bae89035f45341871286a333f749c3141c20573d2b3876e1"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/pytest-dev/pluggy";
        license = licenses.mit;
        description = "plugin and hook calling mechanisms for python";
      };
    };



    "pycodestyle" = python.mkApplication {
      name = "pycodestyle-2.4.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/28/ad/cae9654d7fd64eb3d2ab2c44c9bf8dc5bd4fb759625beab99532239aa6e8/pycodestyle-2.4.0.tar.gz"; sha256 = "cbfca99bd594a10f674d0cd97a3d802a1fdef635d4361e1a2658de47ed261e3a"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://pycodestyle.readthedocs.io/";
        license = licenses.mit;
        description = "Python style guide checker";
      };
    };



    "pydocstyle" = python.mkApplication {
      name = "pydocstyle-2.1.1";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/ca/af/dbd99adec5704de451ae56d08024d7416dead997dedbd6be72cbc86efb08/pydocstyle-2.1.1.tar.gz"; sha256 = "4d5bcde961107873bae621f3d580c3e35a426d3687ffc6f8fb356f6628da5a97"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."six"
      self."snowballstemmer"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/PyCQA/pydocstyle/";
        license = licenses.mit;
        description = "Python docstring style checker";
      };
    };



    "pyflakes" = python.mkApplication {
      name = "pyflakes-2.0.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/92/9e/386c0d9deef14996eb90d9deebbcb9d3ceb70296840b09615cb61b2ae231/pyflakes-2.0.0.tar.gz"; sha256 = "9a7662ec724d0120012f6e29d6248ae3727d821bba522a0e6b356eff19126a49"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/PyCQA/pyflakes";
        license = licenses.mit;
        description = "passive checker of Python programs";
      };
    };



    "python-language-server" = python.mkApplication {
      name = "python-language-server-0.19.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/97/4c/b561716780888f8df9ed44b5e2b8b499258c31b7722d96da0002483fcdd2/python-language-server-0.19.0.tar.gz"; sha256 = "ea40be565429570a318bc010dc8f88250c7bece054880e60704235c3056c6bd8"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [
      self."autopep8"
      self."future"
      self."jedi"
      self."mccabe"
      self."pluggy"
      self."pycodestyle"
      self."pydocstyle"
      self."pyflakes"
      self."rope"
      self."yapf"
    ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/palantir/python-language-server";
        license = "";
        description = "Python Language Server for the Language Server Protocol";
      };
    };



    "rope" = python.mkApplication {
      name = "rope-0.10.7";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/7e/fc/702c0293b57edd4d70146e36f9413c40339a701a43c8fa6918fb9d834913/rope-0.10.7.tar.gz"; sha256 = "a09edfd2034fd50099a67822f9bd851fbd0f4e98d3b87519f6267b60e50d80d1"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/python-rope/rope";
        license = licenses.gpl1;
        description = "a python refactoring library...";
      };
    };



    "six" = python.mkDerivation {
      name = "six-1.11.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/16/d8/bc6316cf98419719bd59c91742194c111b6f2e85abac88e496adefaf7afe/six-1.11.0.tar.gz"; sha256 = "70e8a77beed4562e7f14fe23a786b54f6296e34344c23bc42f07b15018ff98e9"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "http://pypi.python.org/pypi/six/";
        license = licenses.mit;
        description = "Python 2 and 3 compatibility utilities";
      };
    };



    "snowballstemmer" = python.mkApplication {
      name = "snowballstemmer-1.2.1";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/20/6b/d2a7cb176d4d664d94a6debf52cd8dbae1f7203c8e42426daa077051d59c/snowballstemmer-1.2.1.tar.gz"; sha256 = "919f26a68b2c17a7634da993d91339e288964f93c274f1343e3bbbe2096e1128"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "https://github.com/shibukawa/snowball_py";
        license = licenses.bsdOriginal;
        description = "This package provides 16 stemmer algorithms (15 + Poerter English stemmer) generated from Snowball algorithms.";
      };
    };



    "yapf" = python.mkApplication {
      name = "yapf-0.22.0";
      src = pkgs.fetchurl { url = "https://files.pythonhosted.org/packages/68/73/a34efe529fad3fb33c2d1f5bb357d1a8b9382cf0f3053c7468eb5862e9ce/yapf-0.22.0.tar.gz"; sha256 = "a98a6eacca64d2b920558f4a2f78150db9474de821227e60deaa29f186121c63"; };
      doCheck = commonDoCheck;
      buildInputs = commonBuildInputs;
      propagatedBuildInputs = [ ];
      meta = with pkgs.stdenv.lib; {
        homepage = "";
        license = licenses.asl20;
        description = "A formatter for Python code.";
      };
    };

  };
  localOverridesFile = ./requirements_override.nix;
  overrides = import localOverridesFile { inherit pkgs python; };
  commonOverrides = [

  ];
  allOverrides =
    (if (builtins.pathExists localOverridesFile)
     then [overrides] else [] ) ++ commonOverrides;

in python.withPackages
   (fix' (pkgs.lib.fold
            extends
            generated
            allOverrides
         )
   )
