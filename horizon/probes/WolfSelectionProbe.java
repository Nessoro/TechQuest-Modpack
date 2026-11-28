// First-party oracle: official 1.21.1 WolfVariants bootstrap and selection.
// Holder sets are synthetic membership masks; no server, world or player starts.
package techquest.probes;

import com.google.gson.*;
import com.mojang.serialization.Lifecycle;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

public class WolfSelectionProbe {
    static final List<String> NAMES = List.of("pale", "spotted", "snowy", "black", "ashen", "rusty", "woods", "chestnut", "striped");
    static int membership;
    static Object owner, variants;
    static Class<?> key, holder, reference, holderSet, location, registry;
    static Method parse, createReference;
    static List<String> order = new ArrayList<>();

    static Object ref(Object resourceKey) throws Exception {
        return createReference.invoke(null, owner, resourceKey);
    }
    static String name(Object resourceKey) throws Exception {
        return key.getMethod("a").invoke(resourceKey).toString();
    }
    public static void main(String[] args) throws Exception {
        Class.forName("ab").getMethod("a").invoke(null);
        Class.forName("akt").getMethod("a").invoke(null);
        key=Class.forName("akq");holder=Class.forName("jm");reference=Class.forName("jm$c");
        holderSet=Class.forName("jq");location=Class.forName("akr");registry=Class.forName("jz");
        parse=location.getMethod("a",String.class);
        Class<?> holderOwner=Class.forName("jp");
        owner=Proxy.newProxyInstance(holderOwner.getClassLoader(),new Class<?>[]{holderOwner},(p,m,a)->{
            if(m.getName().equals("a"))return a[0]==p;
            throw new AssertionError("unexpected owner call "+m);
        });
        createReference=reference.getMethod("a",holderOwner,key);
        Object registryKey=Class.forName("lu").getField("m").get(null);
        variants=Class.forName("ju").getConstructor(key,Lifecycle.class).newInstance(registryKey,Lifecycle.stable());
        Object registration=Class.forName("jy").getField("a").get(null);
        Object getter=Proxy.newProxyInstance(key.getClassLoader(),new Class<?>[]{Class.forName("jn")},(p,m,a)->{
            Object input=a[0];
            if(key.isInstance(input))return ref(input);
            if(Class.forName("awu").isInstance(input))
                return holderSet.getMethod("a",holderOwner,Class.forName("awu")).invoke(null,owner,input);
            throw new AssertionError("unexpected biome lookup "+m);
        });
        Class<?> bootstrap=Class.forName("qq");
        Object context=Proxy.newProxyInstance(bootstrap.getClassLoader(),new Class<?>[]{bootstrap},(p,m,a)->{
            if(a.length==1)return getter;
            order.add(name(a[0]));
            return variants.getClass().getMethod("a",key,Object.class,Class.forName("jy")).invoke(variants,a[0],a[1],registration);
        });
        Class<?> wolfVariants=Class.forName("cgj");
        wolfVariants.getMethod("a",bootstrap).invoke(null,context);
        variants.getClass().getMethod("m").invoke(variants);
        JsonObject live=JsonParser.parseString(Files.readString(Path.of(args[1]))).getAsJsonObject();
        if(live.get("exit_code").getAsInt()!=0)throw new AssertionError("live reference did not stop cleanly");
        List<String> liveOrder=new ArrayList<>();
        Object loaded=Class.forName("ju").getConstructor(key,Lifecycle.class).newInstance(registryKey,Lifecycle.stable());
        for(var entry:live.getAsJsonArray("live_priority")){
            String id="minecraft:"+entry.getAsString();liveOrder.add(id);
            Object loc=parse.invoke(null,id);
            Object resource=key.getMethod("a",key,location).invoke(null,registryKey,loc);
            Object value=registry.getMethod("a",location).invoke(variants,loc);
            loaded.getClass().getMethod("a",key,Object.class,Class.forName("jy")).invoke(loaded,resource,value,registration);
        }
        if(liveOrder.size()!=9 || new HashSet<>(liveOrder).size()!=9)throw new AssertionError("invalid observed registry order");
        loaded.getClass().getMethod("m").invoke(loaded);variants=loaded;
        Field biomes=Class.forName("cgi").getDeclaredField("k");biomes.setAccessible(true);
        for(Object variant:(Iterable<?>)variants){
            String id=registry.getMethod("b",Object.class).invoke(variants,variant).toString();
            int bit=NAMES.indexOf(id.substring("minecraft:".length()));
            if(bit<0)throw new AssertionError("unexpected built-in wolf variant "+id);
            Object set=Proxy.newProxyInstance(holderSet.getClassLoader(),new Class<?>[]{holderSet},(p,m,a)->{
                if(m.getName().equals("a") && a!=null && a.length==1 && holder.isInstance(a[0]))return (membership&(1<<bit))!=0;
                throw new AssertionError("unexpected holder set call "+m);
            });
            biomes.set(variant,set);
        }
        Class<?> access=Class.forName("ka");
        Object registries=Proxy.newProxyInstance(access.getClassLoader(),new Class<?>[]{access},(p,m,a)->{
            if(m.getName().equals("d") && a[0].equals(registryKey))return variants;
            throw new AssertionError("unexpected registry access "+m);
        });
        Object biome=holder.getMethod("a",Object.class).invoke(null,new Object());
        JsonArray cases=new JsonArray();
        for(membership=0;membership<512;membership++){
            Object result=wolfVariants.getMethod("a",access,holder).invoke(null,registries,biome);
            String selected=name(reference.getMethod("h").invoke(result));
            JsonObject row=new JsonObject();row.addProperty("mask",membership);row.addProperty("selected",selected);cases.add(row);
        }
        JsonObject out=new JsonObject();out.add("bootstrap_order",new Gson().toJsonTree(order));out.add("live_order",new Gson().toJsonTree(liveOrder));out.add("cases",cases);
        out.addProperty("holder_membership_is_synthetic",true);
        Files.writeString(Path.of(args[0]),out.toString());
        System.out.println("Wolf selection masks "+cases.size()+", bootstrap order "+order);
    }
}
