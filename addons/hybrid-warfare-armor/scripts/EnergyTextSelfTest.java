import dev.techquest.hybrid.EnergyText;

/** Pure-Java smoke test, no Minecraft client required. */
public final class EnergyTextSelfTest {
    public static void main(String[] args) {
        assertEquals(0, "0");
        assertEquals(999, "999");
        assertEquals(1000, "1k");
        assertEquals(1234, "1.23k");
        assertEquals(10000, "10k");
        assertEquals(500000, "500k");
        assertEquals(1000000, "1m");
        assertEquals(1250000, "1.25m");
        assertEquals(5072896, "5.07m");
        assertEquals(10000000, "10m");
        assertEquals(-5, "0");
        System.out.println("Compact energy formatting OK");
    }

    private static void assertEquals(int value, String expected) {
        String actual = EnergyText.compact(value);
        if (!expected.equals(actual))
            throw new AssertionError(value + ": expected " + expected + ", got " + actual);
    }
}
