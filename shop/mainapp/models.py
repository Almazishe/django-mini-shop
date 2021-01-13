from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


def get_models_for_count(*model_names):
    return [models.Count(model_name) for model_name in model_names]


def get_product_url(obj, view_name):
    ct_model = obj.__class__._meta.model_name
    return reverse(view_name, kwargs={
        'ct_model': ct_model,
        'slug': obj.slug
    })

class LatestProductsManager:

    @staticmethod
    def get_products_for_main_page(*args, **kwargs):
        with_respect_to = kwargs.get('with_respect_to')
        products = []
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('-id')[:5]
            products.extend(model_products)
        if with_respect_to:
            ct_model = ContentType.objects.filter(model=with_respect_to)
            if ct_model.exists():
                if with_respect_to in args:
                    return sorted(
                        products, key=lambda x: x.__class__._meta.model_name.startswith(with_respect_to), reverse=True
                    )
        return products


class LatestProducts:
    objects = LatestProductsManager()



class CategoryManager(models.Manager):

    CATEGORY_NAME_COUNT_NAME = {
        'Ноутбуки': 'notebook__count',
        'Смартфоны': 'smartphone__count'
    }

    def get_queryset(self):
        return super(CategoryManager, self).get_queryset()

    def get_categories_for_left_sidebar(self):
        models_ = get_models_for_count('notebook', 'smartphone')
        qs = list(self.get_queryset().annotate(*models_))
        data = [
            dict(name=c.name, url=c.get_absolute_url(), count=getattr(c, self.CATEGORY_NAME_COUNT_NAME[c.name]))
            for c in qs
        ]

        return data

class Category(models.Model):

    name = models.CharField("Имя категории", max_length=255)
    slug = models.SlugField(unique=True)

    objects = CategoryManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={
            'slug': self.slug
        })


class Product(models.Model):

    # MIN_RESOLUTION = (400, 400)
    # MAX_RESOLUTION = (800, 800)
    # MAX_IMAGE_SIZE = 3145728

    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE)
    title = models.CharField("Нименование", max_length=255)
    slug = models.SlugField(unique=True)
    image = models.ImageField(verbose_name='Изображение')
    description = models.TextField(verbose_name='Описание', null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')


    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def get_model_name(self):
        return self.__class__.__name__.lower()

    # def save(self, *args, **kwargs):
    #     img = Image.open(self.image)
    #     min_height, min_width = Product.MIN_RESOLUTION
    #     max_height, max_width = Product.MAX_RESOLUTION

    #     if img.height < min_height or img.width < min_width:
    #         raise MinResolutionErrorException("Рзарешение изображения меньше минимального.")
    #     if img.height > max_height or img.width > max_width:
    #         raise MaxResolutionErrorException("Рзарешение изображения больше максимального.")

    #     # new_img = img.convert('RGB')
    #     # resized_new_img = new_img.resize((200, 200), Image.ANTIALIAS)
    #     # filestream = BytesIO()
    #     # resized_new_img.save(filestream, 'JPEG', quality=90)
    #     # resized_new_img.seek(0)
    #     # name = '{}.{}'.format(*self.image.name.split('.'))
    #     # self.image = InMemoryUploadedFile(
    #     #     filestream, 'ImageField', name, 'jpeg/image', sys.getsizeof(resized_new_img), None
    #     # )

    #     super().save(*args, **kwargs)



class CartProduct(models.Model):

    user = models.ForeignKey('Customer', verbose_name='Покупатель', on_delete=models.CASCADE)
    cart = models.ForeignKey('Cart', verbose_name='Корзина', on_delete=models.CASCADE, related_name='related_products')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    qty = models.PositiveIntegerField(default=1)
    final_price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Общая цена')

    def __str__(self):
        return f'Продукт: {self.content_object.title}'

    def save(self, *args, **kwargs):
        self.final_price = self.qty * self.content_object.price
        super().save(*args, **kwargs)

    

class Cart(models.Model):

    owner = models.ForeignKey('Customer', null=True, verbose_name='Владелец', on_delete=models.CASCADE)
    products = models.ManyToManyField(CartProduct, blank=True, related_name='related_cart')
    total_products = models.PositiveIntegerField(default=0)
    final_price = models.DecimalField(default=0, max_digits=9, decimal_places=2, verbose_name='Общая цена')
    in_order = models.BooleanField(default=False)
    for_anonymous_user = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)

class Customer(models.Model):

    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE)
    phone = models.CharField('Номер телефона', max_length=20, null=True, blank=True)
    address = models.CharField('Адрес', max_length=255, null=True, blank=True)
    orders = models.ManyToManyField('Order', verbose_name='Заказы покупателя', related_name='related_customer')

    def __str__(self):
        return f'Покупатель {self.user.first_name} {self.user.last_name}'



class Notebook(Product):

    diagonal = models.CharField("Диагональ", max_length=255)
    display = models.CharField("Тип дисплея", max_length=255)
    processor_freq = models.CharField("Частота процессора", max_length=255)
    ram = models.CharField("Оперативная память", max_length=255)
    video = models.CharField("Видеокарта", max_length=255)
    time_without_charge = models.CharField("Время работы аккумулятора", max_length=255)

    def __str__(self):
        return f'{self.category.name} : {self.title}'

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')



class Smartphone(Product):

    diagonal = models.CharField("Диагональ", max_length=255)
    display = models.CharField("Тип дисплея", max_length=255)
    resolution = models.CharField("Разрешение экрана", max_length=255)
    accum_volume = models.CharField("Лбъем батареи", max_length=255)
    ram = models.CharField("Оперативная память", max_length=255)
    sd = models.BooleanField(default=True, verbose_name='Наличие SD карты')
    sd_volume_max = models.CharField(
        "Максиальный объем встраиваемой памяти", max_length=255, null=True, blank=True)
    main_cam_mp = models.CharField("Главная камера", max_length=255)
    frontal_cam_mp = models.CharField("Фронтальная камера", max_length=255)

    def __str__(self):
        return f'{self.category.name} : {self.title}'

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

    # @property
    # def sd(self):
    #     if self.sd:
    #         return "Да"
    #     return 'Нет'


class Order(models.Model):

    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_READY = 'is_ready'
    STATUS_COMPLETED = 'completed'

    BUYING_TYPE_SELF = 'self'
    BUYING_TYPE_DELIVERY = 'delivery'

    STATUS_CHOICES = (
        (STATUS_NEW, 'Новый заказ'),
        (STATUS_IN_PROGRESS, 'Заказ в обработке'),
        (STATUS_READY, 'Заказ готов'),
        (STATUS_COMPLETED, 'Заказ выполнен'),
    )

    BUYIN_TYPE_CHOICES = (
        (BUYING_TYPE_SELF, 'Самовывоз'),
        (BUYING_TYPE_DELIVERY, 'Доставка'),
    )

    customer = models.ForeignKey(Customer, verbose_name='Покупатель', on_delete=models.CASCADE, related_name='related_orders')
    first_name = models.CharField("Имя", max_length=255)
    last_name = models.CharField("Фамилия", max_length=255)
    phone = models.CharField("Телефон", max_length=255)
    cart = models.ForeignKey(Cart, verbose_name='Корзина', on_delete=models.CASCADE, null=True, blank=True)
    address = models.CharField("Адрес", max_length=255,null=True, blank=True)
    status = models.CharField("Статус заказа", max_length=100, choices=STATUS_CHOICES, default=STATUS_NEW)
    buying_type = models.CharField("Тип заказа", max_length=100, choices=BUYIN_TYPE_CHOICES, default=BUYING_TYPE_SELF)
    comment = models.TextField("Комментарий", null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True, verbose_name='Дата создания заказа')
    order_date = models.DateField(verbose_name='Дата получения заказа', default=timezone.now)


    def __str__(self):
        return str(self.id)

