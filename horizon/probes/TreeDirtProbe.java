// First-party 1.21.1 reflection probe; binds the original dirt tag before testing.
// Tests all block states; no game files or worlds are distributed.
package techquest.probes;
import java.lang.reflect.*;
public class TreeDirtProbe {
 public static void main(String[] args)throws Exception{
  Class.forName("ab").getMethod("a").invoke(null);Class.forName("akt").getMethod("a").invoke(null);
  Object blocks=Class.forName("lt").getField("e").get(null);
  Class<?> registry=Class.forName("jz"),location=Class.forName("akr"),tagType=Class.forName("awu");
  Method parse=location.getMethod("a",String.class),get=registry.getMethod("a",location),wrap=registry.getMethod("e",Object.class);
  Object registryKey=registry.getMethod("d").invoke(blocks);
  Object tag=tagType.getMethod("a",registryKey.getClass(),location).invoke(null,registryKey,parse.invoke(null,"minecraft:dirt"));
  var stream=TreeDirtProbe.class.getClassLoader().getResourceAsStream("data/minecraft/tags/block/dirt.json");
  var json=com.google.gson.JsonParser.parseReader(new java.io.InputStreamReader(stream,java.nio.charset.StandardCharsets.UTF_8)).getAsJsonObject();
  java.util.List<Object> members=new java.util.ArrayList<>();
  for(var v:json.getAsJsonArray("values")){String name=v.getAsString();if(name.startsWith("#"))throw new AssertionError("nested dirt tag requires review");members.add(wrap.invoke(blocks,get.invoke(blocks,parse.invoke(null,name))));}
  registry.getMethod("a",java.util.Map.class).invoke(blocks,java.util.Map.of(tag,members));
  Method key=Class.forName("jz").getMethod("b",Object.class);
  Method state=Class.forName("dfy").getMethod("o");
  Method isDirt=Class.forName("ehm").getDeclaredMethod("b",Class.forName("dtc"));isDirt.setAccessible(true);
  int total=0;java.util.List<String> names=new java.util.ArrayList<>();
  int states=0; Method definition=Class.forName("dfy").getMethod("l"),variants=Class.forName("dtd").getMethod("a");
  for(Object block:(Iterable<?>)blocks){total++;boolean expected=(boolean)isDirt.invoke(null,state.invoke(block));if(expected)names.add(key.invoke(blocks,block).toString());
   for(Object v:(Iterable<?>)variants.invoke(definition.invoke(block))){states++;if((boolean)isDirt.invoke(null,v)!=expected)throw new AssertionError("soil predicate depends on properties");}}
  System.out.println("TREE_STATES="+states);
  System.out.println("TREE_DIRT="+total+":"+String.join(",",names));
 }
}
