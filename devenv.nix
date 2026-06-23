{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/packages/
  packages = with pkgs; [
    git
    poppler-utils  # Requirement for running.
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    venv.enable = true;
    uv = {
      enable = true;
      sync = {
        enable = true;
        groups = ["nox"];
      };
    };
  };

  # https://devenv.sh/basics/
  enterShell = '''';

  # https://devenv.sh/git-hooks/
  # git-hooks.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
