package dev.techquest.hybrid;

import java.math.BigDecimal;
import java.math.RoundingMode;

/** Locale-independent tooltip shorthand for power levels: 5.07m / 10m. */
public final class EnergyText {
    private EnergyText() {}

    public static String compact(int amount) {
        if (amount < 0) amount = 0;
        if (amount < 1_000) return Integer.toString(amount);
        int divisor = amount >= 1_000_000 ? 1_000_000 : 1_000;
        String suffix = divisor == 1_000_000 ? "m" : "k";
        return BigDecimal.valueOf(amount)
                .divide(BigDecimal.valueOf(divisor), 2, RoundingMode.HALF_UP)
                .stripTrailingZeros()
                .toPlainString() + suffix;
    }
}
