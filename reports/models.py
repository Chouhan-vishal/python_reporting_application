from django.db import models

# Create your models here.
class ProductGroup(models.Model):
    item_details = models.CharField(max_length=100)
    item_category = models.CharField(max_length=100)
    item_group = models.CharField(max_length=100)
    cost = models.IntegerField()

    def __str__(self):
        return f"{self.item_details} - {self.item_group}"
