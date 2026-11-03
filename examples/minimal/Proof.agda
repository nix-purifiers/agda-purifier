module Proof where
open import Prelude
answer : Nat
answer = id 42
proof : answer ≡ 42
proof = refl
