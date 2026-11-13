// First-party reflection probe, pinned Minecraft 1.21.1 official mappings.
// No decompilation, game server or client launch; see TERRALITH_RUNTIME_RU.md.
package techquest.probes;
import java.lang.reflect.*;
public class SamplerProbe {
 public static void main(String[] args)throws Exception {
  Class.forName("ab").getMethod("a").invoke(null); Class.forName("akt").getMethod("a").invoke(null);
  Class<?> random=Class.forName("ayw"),normal=Class.forName("eoh"),holder=Class.forName("jm"),nh=Class.forName("dyr$c"),df=Class.forName("dyr"),fc=Class.forName("dyr$b"),point=Class.forName("dyr$e"),sampler=Class.forName("dys$z"),mapper=Class.forName("dys$z$a");
  Object rand=Class.forName("dyz").getConstructor(long.class).newInstance(263L);
  Object noise=normal.getMethod("a",random,int.class,double[].class).invoke(null,rand,-3,new double[]{1.0});
  Constructor<?> hc=nh.getDeclaredConstructor(holder,normal);hc.setAccessible(true);Object noiseHolder=hc.newInstance(null,noise);
  Constructor<?> sc=sampler.getDeclaredConstructor(df,nh,mapper);sc.setAccessible(true);
  Method transform=sampler.getDeclaredMethod("a",fc,double.class);transform.setAccessible(true);
  Method value=normal.getMethod("a",double.class,double.class,double.class);
  Class<?> rarity=Class.forName("dzf$a");Method two=rarity.getDeclaredMethod("a",double.class),three=rarity.getDeclaredMethod("b",double.class);two.setAccessible(true);three.setAccessible(true);
  int tests=0;double error=0;
  for(Object kind:mapper.getEnumConstants()){
   Object instance=sc.newInstance(null,noiseHolder,kind);boolean type1=((Enum<?>)kind).name().equals("TYPE1");Method map=type1?three:two;
   for(double input:new double[]{-2,-.75,-.5,0,.5,.75,2})for(int[] xyz:new int[][]{{0,0,0},{17,-23,61},{-1023,128,-2049},{999999,300,555555}}){
    Object context=point.getDeclaredConstructor(int.class,int.class,int.class).newInstance(xyz[0],xyz[1],xyz[2]);
    double scale=(double)map.invoke(null,input);double expected=scale*Math.abs((double)value.invoke(noise,xyz[0]/scale,xyz[1]/scale,xyz[2]/scale));
    double observed=(double)transform.invoke(instance,context,input);error=Math.max(error,Math.abs(expected-observed));if(expected!=observed)throw new AssertionError("Sampler formula mismatch");tests++;
   }
  }
  System.out.println("{\"samples\":"+tests+",\"max_formula_error\":"+error+"}");
 }
}
