# Risk checklist: Numbers and time

Area file of [risk-checklist.md](../risk-checklist.md); apply its How to use.

| Item | Signal | What to check |
|---|---|---|
| Money | Prices, payments, fees, taxes, settlements | Integers or fixed decimals instead of floating point, where and how rounding happens, currency, difference between the total and the sum of items |
| Quantity and units | Unit conversion (box↔piece, kg↔g), fractional quantities | Source of the conversion basis, accumulated conversion error |
| Time zone | Date-based aggregation, cut-off times, overseas users or servers | Stored time zone, displayed time zone, what "today" means |
| Business days | Delivery dates, settlement dates, validity periods | Holidays and weekends, whether boundary days are included |
