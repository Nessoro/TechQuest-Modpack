package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Runtime Inventory.add contract needed by filled Oritech portable tanks. */
@Mod("techquest_reference_probe")
public final class OritechInventoryLimitsProbe {
    public OritechInventoryLimitsProbe(){NeoForge.EVENT_BUS.addListener(this::started);}
    private static ItemStack stack(String id,int count,int limit){
        var s=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)),count);
        if(limit>0)s.set(DataComponents.MAX_STACK_SIZE,limit);return s;
    }
    private static List<Object> inventory(FakePlayer p){
        var rows=new ArrayList<Object>();for(int i=0;i<p.getInventory().getContainerSize();i++){
            var s=p.getInventory().getItem(i);if(!s.isEmpty())rows.add(Map.of("slot",i,"item",BuiltInRegistries.ITEM.getKey(s.getItem()).toString(),"count",s.getCount(),"maximum",s.getMaxStackSize()));
        }return rows;
    }
    private void started(ServerStartedEvent event){
        var server=event.getServer();try{
            server.tickRateManager().setFrozen(true);var p=new FakePlayer(server.overworld(),new GameProfile(UUID.fromString("a2663000-0000-4000-8000-000000000011"),"TQMaxRef"));p.setGameMode(GameType.SURVIVAL);
            var rows=new ArrayList<Object>();
            for(String id:new String[]{"minecraft:stone","minecraft:ender_pearl"})for(int limit:new int[]{0,1,2,16,64,99})for(int count:new int[]{1,2,64,100})for(int mode:new int[]{0,1,2,3}){
                p.getInventory().clearContent();p.getInventory().selected=0;
                if(mode==1)p.getInventory().setItem(0,stack(id,1,limit));
                if(mode==2){p.getInventory().setItem(0,stack(id,1,limit));p.getInventory().setItem(40,stack(id,1,limit));}
                if(mode==3)for(int i=0;i<36;i++)p.getInventory().setItem(i,stack("minecraft:barrier",64,0));
                var initial=inventory(p);var incoming=stack(id,count,limit);boolean added=p.getInventory().add(incoming);
                rows.add(Map.of("name","case_"+rows.size(),"item",id,"limit_override",limit,"count",count,"mode",mode,"initial",initial,"after",inventory(p),"returned_success",added,"remaining",incoming.getCount()));
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(Map.of("schema",1,"original_inventory_add_executed",true,"rows",rows,"driver","Survival FakePlayer Inventory.add with synthetic selected/offhand/full inventory and explicit max-stack component; no real player or network claim")));
        }catch(Exception e){throw new IllegalStateException("Original inventory limit fixture failed",e);}finally{server.halt(false);}
    }
}
