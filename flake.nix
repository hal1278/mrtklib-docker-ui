{
  description = "MRTKLIB Web UI with Docker and Nix workflows";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    mrtklib-src = {
      url = "github:h-shiono/MRTKLIB/v0.7.6";
      flake = false;
    };
  };

  outputs =
    { self, nixpkgs, mrtklib-src }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];

      forAllSystems = f:
        nixpkgs.lib.genAttrs systems (system:
          f {
            inherit system;
            pkgs = import nixpkgs { inherit system; };
          });
    in
    {
      devShells = forAllSystems ({ pkgs, system, ... }:
        let
          nodejs = if pkgs ? nodejs_22 then pkgs.nodejs_22 else pkgs.nodejs;
          mrtklibPackage = self.packages.${system}.mrtklib;
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.python312
              pkgs.ruff
              pkgs.uv
              nodejs
              pkgs.cmake
              pkgs.git
              pkgs.openblasCompat
              mrtklibPackage
            ];

            shellHook = ''
              export MRTKLIB_WORKSPACE_DIR="$PWD/workspace"
              export MRTKLIB_DATA_DIR="$PWD/data"
              export MRTKLIB_MRTK_BIN="${mrtklibPackage}/bin/mrtk"
              export MRTKLIB_SYSTEM_DIR="${mrtklibPackage}/share/mrtklib"
              export MRTKLIB_CORRECTIONS_DIR="$MRTKLIB_SYSTEM_DIR/corrections"
              export MRTKLIB_CREDENTIALS_FILE="$MRTKLIB_WORKSPACE_DIR/.credentials.toml"
              export MRTKLIB_NETRC_PATH="$MRTKLIB_WORKSPACE_DIR/.netrc"
              mkdir -p "$MRTKLIB_WORKSPACE_DIR" "$MRTKLIB_DATA_DIR"
              echo "MRTKLIB Nix development shell ready."
            '';
          };
        });

      packages = forAllSystems ({ pkgs, system }:
        let
          lib = pkgs.lib;
          nodejs = if pkgs ? nodejs_22 then pkgs.nodejs_22 else pkgs.nodejs;
          python = pkgs.python312;
          pythonPackages = python.pkgs;

          cleanFilter = path: type:
            let
              base = builtins.baseNameOf path;
            in
            !builtins.elem base [
              ".codex"
              ".direnv"
              ".git"
              ".pytest_cache"
              "__pycache__"
              "dist"
              "node_modules"
              "result"
            ];

          repoSrc = lib.cleanSourceWith {
            src = ./.;
            filter = cleanFilter;
          };

          frontendSrc = lib.cleanSourceWith {
            src = ./frontend;
            filter = cleanFilter;
          };

          version =
            if self ? shortRev then
              "0.0.0+git.${self.shortRev}"
            else
              "0.0.0+dirty";

          mrtklib = pkgs.stdenv.mkDerivation {
            pname = "mrtklib";
            inherit version;

            src = mrtklib-src;

            nativeBuildInputs = [
              pkgs.cmake
              pkgs.gnutar
              pkgs.gzip
            ];
            buildInputs = [ pkgs.openblasCompat ];

            cmakeFlags = [
              "-DCMAKE_BUILD_TYPE=Release"
              "-DBLA_VENDOR=OpenBLAS"
              "-DBLA_SIZEOF_INTEGER=4"
            ];

            installPhase = ''
              runHook preInstall
              install -Dm755 mrtk $out/bin/mrtk

              mkdir -p \
                $out/share/mrtklib/corrections/clas \
                $out/share/mrtklib/corrections/madoca \
                $out/share/mrtklib/clas-presets \
                $out/share/mrtklib/presets

              tar xzf $src/tests/data/claslib/claslib_testdata.tar.gz \
                -C $out/share/mrtklib/corrections/clas \
                clas_grid.def clas_grid.blq igu00p01.erp \
                igs14_L5copy.atx isb.tbl l2csft.tbl
              tar xzf $src/tests/data/madocalib/madocalib_testdata.tar.gz \
                -C $out/share/mrtklib/corrections/madoca \
                igs20.atx

              cp -r ${./docker/clas-presets}/. \
                $out/share/mrtklib/clas-presets/
              cp -r ${./docker/bundled-presets}/. \
                $out/share/mrtklib/presets/

              if [ -d $src/conf ]; then
                cp -r $src/conf $out/share/mrtklib/conf
              fi
              runHook postInstall
            '';
          };

          frontend = pkgs.buildNpmPackage {
            pname = "mrtklib-web-ui-frontend";
            inherit version;
            src = frontendSrc;

            nativeBuildInputs = [ nodejs ];
            npmDepsHash = "sha256-NwTNwHfjXAFS/DJPnqNzCjvTknXyq+tBEmoCVnJDKc8=";
            npmBuildScript = "build";

            installPhase = ''
              runHook preInstall
              mkdir -p $out/share/mrtklib-web-ui/static
              cp -r dist/* $out/share/mrtklib-web-ui/static/
              runHook postInstall
            '';
          };

          backendDeps =
            with pythonPackages;
            [
              fastapi
              httpx
              numpy
              pydantic
              uvicorn
              websockets
              watchfiles
              pythonPackages."python-multipart"
              pythonPackages."python-socketio"
            ]
            ++ lib.optionals (pythonPackages ? cssrlib) [ pythonPackages.cssrlib ];

          backend = pythonPackages.buildPythonApplication {
            pname = "mrtklib-web-ui-backend";
            inherit version;
            pyproject = true;
            src = repoSrc;

            build-system = with pythonPackages; [
              hatch-vcs
              hatchling
            ];

            dependencies = backendDeps;
            nativeBuildInputs = [ pkgs.gitMinimal ];

            env.SETUPTOOLS_SCM_PRETEND_VERSION = version;

            doCheck = false;
            pythonImportsCheck = [ "mrtklib_web_ui.main" ];
          };

          defaultAppPackage = pkgs.writeShellApplication {
            name = "mrtklib-web-ui";
            text = ''
              export MRTKLIB_WORKSPACE_DIR="${"$"}{MRTKLIB_WORKSPACE_DIR:-$PWD/workspace}"
              export MRTKLIB_DATA_DIR="${"$"}{MRTKLIB_DATA_DIR:-$PWD/data}"
              export MRTKLIB_MRTK_BIN="${"$"}{MRTKLIB_MRTK_BIN:-${mrtklib}/bin/mrtk}"
              export MRTKLIB_SYSTEM_DIR="${"$"}{MRTKLIB_SYSTEM_DIR:-${mrtklib}/share/mrtklib}"
              export MRTKLIB_CORRECTIONS_DIR="${"$"}{MRTKLIB_CORRECTIONS_DIR:-${"$"}MRTKLIB_SYSTEM_DIR/corrections}"
              export MRTKLIB_STATIC_DIR="${"$"}{MRTKLIB_STATIC_DIR:-${frontend}/share/mrtklib-web-ui/static}"
              export MRTKLIB_NETRC_PATH="${"$"}{MRTKLIB_NETRC_PATH:-${"$"}MRTKLIB_WORKSPACE_DIR/.netrc}"
              export MRTKLIB_CREDENTIALS_FILE="${"$"}{MRTKLIB_CREDENTIALS_FILE:-${"$"}MRTKLIB_WORKSPACE_DIR/.credentials.toml}"

              mkdir -p "$MRTKLIB_WORKSPACE_DIR" "$MRTKLIB_DATA_DIR"

              exec ${backend}/bin/mrtklib-web-ui "$@"
            '';
          };
        in
        {
          inherit backend frontend mrtklib;
          default = defaultAppPackage;
        });

      apps = forAllSystems ({ system, ... }: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/mrtklib-web-ui";
        };
      });

      checks = forAllSystems ({ system, ... }: {
        mrtklib = self.packages.${system}.mrtklib;
        frontend = self.packages.${system}.frontend;
        backend = self.packages.${system}.backend;
        default = self.packages.${system}.default;
      });
    };
}
