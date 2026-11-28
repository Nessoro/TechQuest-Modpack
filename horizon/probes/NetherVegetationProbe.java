// First-party recording-world oracle for the official 1.21.1 nether vegetation loop.
package techquest.probes;

import com.google.gson.*;
import com.mojang.serialization.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

public class NetherVegetationProbe {
    static Class<?> registry, location, state, position, world, random, context;
    static Object blocks, feature, config, air, stone;
    static Method parse, get, defaultState, isAir;
    static List<Object> palette = new ArrayList<>();
    static List<String> names = List.of("minecraft:stone", "minecraft:dirt", "minecraft:granite",
        "minecraft:andesite", "minecraft:diorite", "minecraft:blackstone");
    static int[] weights = {3,7,20,20,20,50};

    static Object block(String name) throws Exception {
        return get.invoke(blocks, parse.invoke(null, name));
    }
    static Object read(Object pos, Object support, int originY, String mode) throws Exception {
        int x=(Integer)position.getMethod("u").invoke(pos), y=(Integer)position.getMethod("v").invoke(pos),
            z=(Integer)position.getMethod("w").invoke(pos);
        if (x==0 && y==originY-1 && z==0) return support;
        boolean empty = mode.equals("all") || (mode.equals("mixed") && Math.floorMod(x*31+y*7+z*17,3)!=0);
        return empty ? air : stone;
    }
    static JsonObject run(String supportName, String mode, int originY, long seed) throws Exception {
        Object support=defaultState.invoke(block(supportName));
        JsonArray writes=new JsonArray();
        Object level=Proxy.newProxyInstance(world.getClassLoader(),new Class<?>[]{world},(p,m,a)->{
            if(m.getName().equals("I_"))return -64;
            if(m.getName().equals("J_"))return 384;
            if(m.getName().equals("am"))return 320;
            if(m.getName().equals("f_"))return true;
            if(m.getReturnType()==state)return read(a[0],support,originY,mode);
            if(m.getName().equals("u"))return isAir.invoke(read(a[0],support,originY,mode));
            if(a!=null && a.length==3 && position.isInstance(a[0]) && state.isInstance(a[1])){
                if(!a[2].equals(2))throw new AssertionError("unexpected placement flags");
                int index=palette.indexOf(a[1]);
                if(index<0)throw new AssertionError("unexpected selected block");
                JsonArray xyz=new JsonArray();
                for(String axis:List.of("u","v","w"))xyz.add((Integer)position.getMethod(axis).invoke(a[0]));
                JsonObject mutation=new JsonObject();mutation.add("position",xyz);
                mutation.addProperty("block",names.get(index));writes.add(mutation);return true;
            }
            throw new AssertionError("unexpected world query "+m);
        });
        Object rng=Class.forName("dyz").getConstructor(long.class).newInstance(seed);
        Object at=position.getConstructor(int.class,int.class,int.class).newInstance(0,originY,0);
        Object ctx=context.getConstructor(Optional.class,world,Class.forName("duz"),random,position,Class.forName("eei"))
            .newInstance(Optional.empty(),level,null,rng,at,config);
        boolean result=(Boolean)Class.forName("ece").getMethod("a",context).invoke(feature,ctx);
        JsonObject row=new JsonObject();row.addProperty("support",supportName);row.addProperty("mode",mode);
        row.addProperty("origin_y",originY);row.addProperty("seed",seed);row.addProperty("result",result);
        row.add("writes",writes);row.addProperty("tail",(Integer)random.getMethod("a",int.class).invoke(rng,1000000007));
        return row;
    }
    @SuppressWarnings("unchecked")
    public static void main(String[] args)throws Exception{
        Class.forName("ab").getMethod("a").invoke(null);Class.forName("akt").getMethod("a").invoke(null);
        registry=Class.forName("jz");location=Class.forName("akr");state=Class.forName("dtc");position=Class.forName("jd");
        world=Class.forName("dds");random=Class.forName("ayw");context=Class.forName("ecg");
        blocks=Class.forName("lt").getField("e").get(null);parse=location.getMethod("a",String.class);
        get=registry.getMethod("a",location);defaultState=Class.forName("dfy").getMethod("o");isAir=state.getMethod("i");
        var stream=NetherVegetationProbe.class.getClassLoader().getResourceAsStream("data/minecraft/tags/block/nylium.json");
        JsonObject original=JsonParser.parseReader(new java.io.InputStreamReader(stream)).getAsJsonObject();
        List<String> tagNames=new ArrayList<>();for(var value:original.getAsJsonArray("values"))tagNames.add(value.getAsString());
        JsonObject extra=JsonParser.parseString(Files.readString(Path.of(args[0]).resolve(
            "mods/terralith/carry/data/minecraft/tags/block/nylium.json"))).getAsJsonObject();
        if(extra.get("replace").getAsBoolean())throw new AssertionError("review replaced nylium tag");
        for(var value:extra.getAsJsonArray("values"))tagNames.add(value.getAsString());
        Object registryKey=registry.getMethod("d").invoke(blocks);
        Object tag=Class.forName("awu").getMethod("a",registryKey.getClass(),location).invoke(null,registryKey,parse.invoke(null,"minecraft:nylium"));
        List<Object> members=new ArrayList<>();for(String name:tagNames){
            if(name.startsWith("#"))throw new AssertionError("review nested nylium tag");
            members.add(registry.getMethod("e",Object.class).invoke(blocks,block(name)));
        }
        registry.getMethod("a",Map.class).invoke(blocks,Map.of(tag,members));
        air=defaultState.invoke(block("minecraft:air"));stone=defaultState.invoke(block("minecraft:stone"));
        JsonArray entries=new JsonArray();for(int i=0;i<names.size();i++){
            palette.add(defaultState.invoke(block(names.get(i))));JsonObject entry=new JsonObject(),data=new JsonObject();
            data.addProperty("Name",names.get(i));entry.add("data",data);entry.addProperty("weight",weights[i]);entries.add(entry);
        }
        JsonObject provider=new JsonObject();provider.addProperty("type","minecraft:weighted_state_provider");provider.add("entries",entries);
        Class<?> providerType=Class.forName("egj");Codec<Object> codec=(Codec<Object>)providerType.getField("a").get(null);
        Object selected=codec.parse(JsonOps.INSTANCE,provider).getOrThrow();
        config=Class.forName("eeo").getConstructor(providerType,int.class,int.class).newInstance(selected,8,4);
        feature=get.invoke(Class.forName("lt").getField("O").get(null),parse.invoke(null,"minecraft:nether_forest_vegetation"));
        JsonArray cases=new JsonArray(),airNames=new JsonArray();Method key=registry.getMethod("b",Object.class);
        for(Object block:(Iterable<?>)blocks)if((Boolean)isAir.invoke(defaultState.invoke(block)))airNames.add(key.invoke(blocks,block).toString());
        for(String support:List.of("minecraft:crimson_nylium","minecraft:warped_nylium","minecraft:grass_block","minecraft:mycelium","minecraft:moss_block","minecraft:stone"))
            for(String mode:List.of("all","mixed","none"))for(int y:new int[]{80,-64,-63,318,319})
                for(long seed:new long[]{0,1,-1,263,Long.MAX_VALUE})cases.add(run(support,mode,y,seed));
        JsonObject out=new JsonObject();out.add("air_blocks",airNames);out.add("cases",cases);
        Files.writeString(Path.of(args[1]),out.toString());System.out.println("Nether vegetation cases "+cases.size()+", air "+airNames);
    }
}
