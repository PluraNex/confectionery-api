from stock.services.orchestrator import StockOrchestrator

@receiver(post_save, sender=SupplyBatch)
def create_stock_from_batch(sender, instance, created, **kwargs):
    if created:
        StockOrchestrator.auto_add_to_stock(instance)
