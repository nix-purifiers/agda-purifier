{-# LANGUAGE OverloadedStrings #-}
import Agda.Interaction.Library
import Agda.Interaction.Library.Base (runLibM)
import Agda.Syntax.Common.Pretty (prettyShow)
import Agda.Utils.Null (empty)
import Data.Aeson
import qualified Data.ByteString.Lazy.Char8 as B
import System.Environment
import System.Exit

main = do
  args <- getArgs
  ((result, warnings), _) <- runLibM (case args of
    ["--metadata", libraries] -> do
      installed <- getInstalledLibraries (Just libraries)
      pure $ object ["libraries" .= map (record installed) installed]
    [project, libraries] -> do
      installed <- getInstalledLibraries (Just libraries)
      roots <- getAgdaLibFile project
      (names, includes) <- getDefaultLibraries project False
      paths <- libraryIncludePaths (Just libraries) installed names
      pure $ object
        [ "project" .= map (record installed) roots
        , "requirements" .= map prettyShow names
        , "includes" .= includes
        , "paths" .= paths
        , "libraries" .= map (record installed) (selected installed [] names)
        ]
    _ -> error "Expected PROJECT LIBRARIES or --metadata LIBRARIES") empty
  case result of
    Left e -> print e >> exitFailure
    Right value -> B.putStrLn (encode value)
  where
    selected _ _ [] = []
    selected installed seen (name:names)
      | prettyShow name == "." = selected installed seen names
      | name `elem` seen = selected installed seen names
      | otherwise = case findLib' _libName name installed of
          [library] -> library : selected installed (name:seen) (_libDepends library ++ names)
          _ -> error "Native libraryIncludePaths accepted an unresolved library"
    resolved installed name
      | prettyShow name == "." = "."
      | otherwise = case findLib' _libName name installed of
          [library] -> prettyShow (_libName library)
          _ -> error "Native resolver accepted an unresolved dependency"
    record installed l = object
      [ "name" .= prettyShow (_libName l)
      , "file" .= _libFile l
      , "includes" .= _libIncludes l
      , "dependencies" .= map (resolved installed) (_libDepends l)
      , "requests" .= map prettyShow (_libDepends l)
      ]
