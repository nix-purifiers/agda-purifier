final: prev: {
  agda-purifier = {
    readLock = import ./read-lock.nix { lib = final; };
  };
}
