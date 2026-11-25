{-# LANGUAGE OverloadedStrings #-}
import Agda.Compiler.JS.Compiler (jsFileName, jsMod)
import Agda.Compiler.JS.Pretty (JSModuleStyle(JSES6))
import Agda.Interaction.Imports (parseSource, Source(..))
import Agda.TypeChecking.Monad (runTCMTop, srcFromPath)
import Agda.Syntax.Common.Pretty (prettyShow)
import Agda.Setup (getDataDir)
import Agda.Utils.FileName (absolute)
import Agda.Syntax.Parser (agdaFileExtensions)
import Data.Aeson
import qualified Data.ByteString.Lazy.Char8 as B
import System.Environment
import System.Exit

main = do
  [filename] <- getArgs
  path <- absolute filename
  result <- runTCMTop $ parseSource =<< srcFromPath path
  case result of
    Left e -> print e >> exitFailure
    Right parsed -> do
      dataDir <- getDataDir
      B.putStrLn $ encode $ object
        [ "module" .= prettyShow (srcModuleName parsed)
        , "nativeOutput" .= jsFileName JSES6 (jsMod (srcModuleName parsed))
        , "sdkData" .= dataDir
        , "sourceExtensions" .= agdaFileExtensions
        ]
