import java.nio.file.*;
import java.util.Arrays;
class JavascriptResource {
  public static void main(String[] args) throws Exception {
    for (String name : args) {
      try (var bytes = JavascriptResource.class.getResourceAsStream(System.getProperty("prefix", "/") + Path.of(name).getFileName())) {
        if (bytes == null || !Arrays.equals(bytes.readAllBytes(), Files.readAllBytes(Path.of(name))))
          throw new AssertionError(name);
      }
    }
  }
}
