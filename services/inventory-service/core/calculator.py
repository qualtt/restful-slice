class Calculator:
    @staticmethod
    def calculate_cost(
        weight_grams: float,
        price_per_gram: float,
        markup_percent: float
    ) -> float:
        """
        Расчет стоимости печати:
        Стоимость пластика * наценку профиля
        """
        if weight_grams < 0:
            raise ValueError("Вес не может быть отрицательным")
        
        if price_per_gram < 0 or markup_percent < 0:
            raise ValueError("Расценки/наценка не могут быть отрицательными")
            
        cost = weight_grams * price_per_gram * markup_percent
        return round(cost, 2)
