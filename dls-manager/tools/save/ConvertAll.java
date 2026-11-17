package com.dlsmgr;
import java.nio.file.*;
import org.json.JSONObject;
public class ConvertAll {
  public static void main(String[] a) throws Exception {
    byte[] f = Files.readAllBytes(Paths.get(a[0]));
    JSONObject clubs = new JSONObject(new String(Files.readAllBytes(Paths.get(a[1])), "UTF-8"));
    Files.createDirectories(Paths.get(a[2]));
    for (String cid : clubs.keySet()) {
      try {
        byte[] out = Profile.encode(Profile.becomeClub(Profile.decode(f), clubs.getJSONObject(cid)));
        Files.write(Paths.get(a[2], cid + ".dat"), out);
      } catch (Throwable t) { System.out.println(cid + " FAILED " + t); }
    }
  }
}
