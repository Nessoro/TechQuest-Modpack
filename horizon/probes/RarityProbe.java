// First-party reflection probe, pinned Minecraft 1.21.1 official mappings.
// No decompilation, game server or client launch; see TERRALITH_RUNTIME_RU.md.
package techquest.probes;
import java.lang.reflect.*;
public class RarityProbe {
 public static void main(String[] args) throws Exception {
  Class<?> c=Class.forName("dzf$a");
  Method two=c.getDeclaredMethod("a",double.class),three=c.getDeclaredMethod("b",double.class);two.setAccessible(true);three.setAccessible(true);
  System.out.print("{\"type_1\":[");
  float[] cuts={-.75f,-.5f,0f,.5f,.75f};
  java.util.TreeSet<Double> points=new java.util.TreeSet<>();points.add(-2.0);points.add(2.0);
  for(float x:cuts){points.add((double)Math.nextDown(x));points.add((double)x);points.add((double)Math.nextUp(x));}
  int i=0;for(double x:points){if(i++>0)System.out.print(",");System.out.print("["+x+","+three.invoke(null,x)+"]");}
  System.out.print("],\"type_2\":[");i=0;for(double x:points){if(i++>0)System.out.print(",");System.out.print("["+x+","+two.invoke(null,x)+"]");}
  System.out.println("]}");
 }
}
