import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Калькулятор юнит-экономики", layout="wide")
st.title("📊 Калькулятор юнит-экономики (B2C кредитование)")
st.markdown("Введите параметры для **нового** и **повторного** займов. LTV/CAC рассчитывается с учётом CAC повторного займа.")

# --------------------------------------------------------------
# БОКОВАЯ ПАНЕЛЬ – ПАРАМЕТРЫ НОВОГО ЗАЙМА
# --------------------------------------------------------------
with st.sidebar:
    st.header("🆕 Параметры нового займа")
    
    # Основные условия
    st.subheader("💰 Условия займа")
    L_new = st.number_input("Сумма займа (₽)", value=10000.0, step=500.0, key="L_new")
    t_new = st.number_input("Срок (дней)", value=30, step=5, key="t_new")
    r_new = st.number_input("Процентная ставка (% в день)", value=1.0, step=0.1, key="r_new") / 100.0
    fee_new = st.number_input("Комиссия за выдачу (% от суммы)", value=5.0, step=0.5, key="fee_new") / 100.0
    
    # Поведение
    st.subheader("🔄 Поведение")
    early_rate_new = st.slider("Доля досрочных погашений", 0.0, 1.0, 0.15, 0.01, key="early_new")
    prolong_pen_new = st.slider("Доля пролонгаций", 0.0, 1.0, 0.20, 0.01, key="prolong_pen_new")
    prolong_term_new = st.number_input("Средний срок пролонгации (дней)", value=45, step=5, key="prolong_term_new")
    default_rate_new = st.slider("Вероятность дефолта (Loss)", 0.0, 0.5, 0.12, 0.01, key="default_new")
    lgd_new = st.slider("LGD (потери при дефолте)", 0.0, 1.0, 0.80, 0.05, key="lgd_new")
    
    # Кросс-продукты и страховки
    st.subheader("🛡️ Кросс-продукты и страховки")
    ins_pen_new = st.slider("Проникновение страховок", 0.0, 1.0, 0.25, 0.05, key="ins_pen_new")
    ins_sum_new = st.number_input("Средняя сумма страховки (₽)", value=800.0, step=100.0, key="ins_sum_new")
    ins_margin = 0.95
    cross_pen_new = st.slider("Проникновение кросс-продуктов", 0.0, 1.0, 0.10, 0.05, key="cross_pen_new")
    cross_sum_new = st.number_input("Средняя сумма кросс-продукта (₽)", value=2000.0, step=200.0, key="cross_sum_new")
    cross_margin = 0.90
    vat_factor = 1.2
    
    # Расходы на привлечение и обслуживание (Новый заём)
    st.subheader("💸 Расходы на привлечение (новый заём)")
    cac_direct_new = st.number_input("Прямой CAC (₽)", value=500.0, step=50.0, key="cac_new")
    sms_count_new = st.number_input("Количество СМС", value=6, step=1, key="sms_cnt_new")
    sms_price_new = st.number_input("Цена СМС (₽)", value=3.0, step=0.5, key="sms_price_new")
    kc_cost_new = st.number_input("Колл-центр (₽)", value=59.0, step=10.0, key="kc_new")
    scoring_cost_new = st.number_input("Скоринг (заявка, ₽)", value=49.0, step=10.0, key="scoring_new")
    ident_cost_new = st.number_input("Идентификация (заявка, ₽)", value=150.0, step=10.0, key="ident_new")
    
    # Прочие расходы (общие для всех займов)
    st.subheader("💸 Общие расходы на заём")
    money_transfer_cost = st.number_input("Перевод денег (% от суммы)", value=0.5, step=0.1, key="transfer") / 100.0
    collection_rate = st.slider("Доля просрочки в коллекшн", 0.0, 1.0, 0.30, 0.05, key="coll_rate")
    collection_cost_rate = st.number_input("Стоимость взыскания (% от остатка)", value=7.0, step=1.0, key="coll_cost") / 100.0
    funding_rate = st.number_input("Ставка фондирования (% годовых)", value=19.0, step=1.0, key="funding") / 100.0
    
    # Комиссии за погашение
    st.subheader("💳 Комиссии за погашение")
    repay_fee_inc = st.number_input("Доход комиссии (% от суммы возврата)", value=3.5, step=0.5, key="repay_inc") / 100.0
    repay_fee_exp = st.number_input("Расход комиссии (% от суммы возврата)", value=0.3, step=0.1, key="repay_exp") / 100.0
    
    # Конверсия и отказной трафик (только для новых)
    st.subheader("📊 Конверсия и отказной трафик")
    AR = st.slider("Approval Rate (AR)", 0.0, 1.0, 0.62, 0.01, key="ar")
    TR = st.slider("Take Rate (TR)", 0.0, 1.0, 0.63, 0.01, key="tr")
    lead_price = st.number_input("Цена продажи отказа (₽ за лид)", value=108.0, step=10.0, key="lead_price")
    
    # Продажа просроченного портфеля
    st.subheader("🏷️ Продажа просроченного портфеля")
    portfolio_sale_rate = st.slider("Доля продаваемой просрочки", 0.0, 1.0, 0.80, 0.05, key="ps_rate")
    portfolio_sale_price = st.number_input("Цена продажи (% от остатка)", value=18.0, step=2.0, key="ps_price") / 100.0
    
    # Налог
    tax_rate = st.number_input("Налог на прибыль (%)", value=20.0, step=5.0, key="tax") / 100.0
    
    # ----------------------------------------------------------
    # Параметры ПОВТОРНОГО займа
    # ----------------------------------------------------------
    st.header("🔄 Параметры повторного займа")
    use_repeat = st.checkbox("Учитывать повторный заём", value=True)
    RR = st.number_input("Retention Rate (вероятность повтора)", value=1.0, step=0.05, disabled=not use_repeat)
    
    st.subheader("Условия повторного займа")
    L_repeat = st.number_input("Сумма займа (₽)", value=12000.0, step=500.0, key="L_rep", disabled=not use_repeat)
    t_repeat = st.number_input("Срок (дней)", value=30, step=5, key="t_rep", disabled=not use_repeat)
    r_repeat = st.number_input("Ставка (% в день)", value=0.9, step=0.1, key="r_rep", disabled=not use_repeat) / 100.0
    fee_repeat = st.number_input("Комиссия за выдачу (%)", value=5.0, step=0.5, key="fee_rep", disabled=not use_repeat) / 100.0
    early_rate_repeat = st.slider("Доля досрочных погашений", 0.0, 1.0, 0.10, 0.01, key="early_rep", disabled=not use_repeat)
    prolong_pen_repeat = st.slider("Доля пролонгаций", 0.0, 1.0, 0.15, 0.01, key="prol_pen_rep", disabled=not use_repeat)
    prolong_term_repeat = st.number_input("Срок пролонгации (дней)", value=45, step=5, key="prol_term_rep", disabled=not use_repeat)
    default_rate_repeat = st.slider("Вероятность дефолта", 0.0, 0.5, 0.08, 0.01, key="def_rep", disabled=not use_repeat)
    lgd_repeat = st.slider("LGD", 0.0, 1.0, 0.80, 0.05, key="lgd_rep", disabled=not use_repeat)
    
    # Кросс-продукты и страховки (повтор)
    ins_pen_repeat = st.slider("Проникновение страховок (повтор)", 0.0, 1.0, 0.25, 0.05, key="ins_pen_rep", disabled=not use_repeat)
    ins_sum_repeat = st.number_input("Средняя сумма страховки (₽, повтор)", value=800.0, step=100.0, key="ins_sum_rep", disabled=not use_repeat)
    cross_pen_repeat = st.slider("Проникновение кросс-продуктов (повтор)", 0.0, 1.0, 0.10, 0.05, key="cross_pen_rep", disabled=not use_repeat)
    cross_sum_repeat = st.number_input("Средняя сумма кросс-продукта (₽, повтор)", value=2000.0, step=200.0, key="cross_sum_rep", disabled=not use_repeat)
    
    # Расходы на обслуживание для повторного займа
    st.subheader("💸 Расходы на обслуживание (повторный заём)")
    cac_repeat = st.number_input("CAC повторного займа (₽)", value=100.0, step=50.0, key="cac_rep", disabled=not use_repeat)
    sms_count_repeat = st.number_input("Количество СМС (повтор)", value=3, step=1, key="sms_cnt_rep", disabled=not use_repeat)
    sms_price_repeat = st.number_input("Цена СМС (₽, повтор)", value=3.0, step=0.5, key="sms_price_rep", disabled=not use_repeat)
    kc_cost_repeat = st.number_input("Колл-центр (₽, повтор)", value=30.0, step=10.0, key="kc_rep", disabled=not use_repeat)
    scoring_cost_repeat = st.number_input("Скоринг (повтор, ₽)", value=10.0, step=5.0, key="scoring_rep", disabled=not use_repeat)
    ident_cost_repeat = st.number_input("Идентификация (повтор, ₽)", value=0.0, step=10.0, key="ident_rep", disabled=not use_repeat)

# --------------------------------------------------------------
# ФУНКЦИЯ РАСЧЁТА ДЛЯ ОДНОГО ЗАЙМА
# --------------------------------------------------------------
def calculate_loan(params, is_new=True):
    """
    params: словарь с параметрами займа
    is_new: если True, добавляем расходы на привлечение с делением на AR/TR,
            а также доход от отказного трафика.
            Для повторного займа (is_new=False) используем переданные абсолютные значения.
    """
    L = params['L']
    t = params['t']
    r = params['r']
    fee = params['fee']
    early_rate = params['early_rate']
    default_rate = params['default_rate']
    lgd = params['lgd']
    prolong_pen = params['prolong_pen']
    prolong_term = params['prolong_term']
    ins_pen = params['ins_pen']
    ins_sum = params['ins_sum']
    cross_pen = params['cross_pen']
    cross_sum = params['cross_sum']
    money_transfer_cost = params['money_transfer_cost']
    collection_rate = params['collection_rate']
    collection_cost_rate = params['collection_cost_rate']
    funding_rate = params['funding_rate']
    repay_fee_inc = params['repay_fee_inc']
    repay_fee_exp = params['repay_fee_exp']
    portfolio_sale_rate = params['portfolio_sale_rate']
    portfolio_sale_price = params['portfolio_sale_price']
    tax_rate = params['tax_rate']
    
    if is_new:
        cac_direct = params['cac_direct']
        sms_cost = params['sms_count'] * params['sms_price']
        kc_cost = params['kc_cost']
        scoring_cost = params['scoring_cost']
        ident_cost = params['ident_cost']
        AR = params['AR']
        TR = params['TR']
        lead_price = params['lead_price']
        
        scoring_per_loan = scoring_cost / AR / TR
        ident_per_loan = ident_cost / AR / TR
    else:
        cac_direct = params['cac_direct']   # теперь CAC_repeat
        sms_cost = params['sms_count'] * params['sms_price']
        kc_cost = params['kc_cost']
        scoring_per_loan = params['scoring_cost']
        ident_per_loan = params['ident_cost']
        lead_price = 0
    
    # ----- ДОХОДЫ -----
    interest = L * r * t
    fee_income = L * fee
    cross_income = (cross_margin * cross_pen * cross_sum) / vat_factor
    ins_income = (ins_margin * ins_pen * ins_sum) / vat_factor
    prolong_income = prolong_pen * prolong_term * L * r
    penalty = L * (default_rate * 0.3) * 0.005 * 30
    early_loss = L * r * t * early_rate * 0.5
    portfolio_sale = L * default_rate * (1 + r * t) * portfolio_sale_rate * portfolio_sale_price
    repay_fee_inc_amount = L * (1 + r * t) * (1 - default_rate) * repay_fee_inc
    
    total_revenue = (interest + fee_income + cross_income + ins_income + prolong_income
                     + penalty + portfolio_sale + repay_fee_inc_amount - early_loss)
    
    if is_new:
        rejection_income = lead_price / TR * ((1 - AR) / AR)
        total_revenue += rejection_income
    
    # ----- РАСХОДЫ -----
    cac_total = cac_direct + sms_cost + kc_cost
    money_transfer = L * money_transfer_cost
    collection = collection_rate * (1 - default_rate) * L * collection_cost_rate
    funding = L * (1 + r * t / 2) * (funding_rate / 365) * t
    repay_fee_exp_amount = L * (1 + r * t) * (1 - default_rate) * repay_fee_exp
    
    total_costs = (cac_total + scoring_per_loan + ident_per_loan
                   + money_transfer + collection + funding + repay_fee_exp_amount)
    
    expected_loss = L * default_rate * lgd
    
    profit_before_tax = total_revenue - total_costs - expected_loss
    profit_after_tax = profit_before_tax * (1 - tax_rate)
    
    # Детализация
    revenue_breakdown = {
        'Процентный доход': interest,
        'Комиссия за выдачу': fee_income,
        'Кросс-продукты': cross_income,
        'Страховки': ins_income,
        'Пролонгация': prolong_income,
        'Штрафы': penalty,
        'Продажа портфеля': portfolio_sale,
        'Комиссия за погашение (доход)': repay_fee_inc_amount,
        'Потеря от досрочки': -early_loss,
    }
    if is_new:
        revenue_breakdown['Отказной трафик'] = rejection_income
    
    cost_breakdown = {
        'CAC (прямой)': cac_direct,
        'СМС': sms_cost,
        'Колл-центр': kc_cost,
        'Скоринг (на заём)': scoring_per_loan,
        'Идентификация (на заём)': ident_per_loan,
        'Перевод денег': money_transfer,
        'Взыскание': collection,
        'Фондирование': funding,
        'Комиссия за погашение (расход)': repay_fee_exp_amount,
        'Ожидаемые потери (ECL)': expected_loss,
    }
    
    return profit_after_tax, revenue_breakdown, cost_breakdown, profit_before_tax

# --------------------------------------------------------------
# СБОР ПАРАМЕТРОВ ДЛЯ НОВОГО И ПОВТОРНОГО ЗАЙМА
# --------------------------------------------------------------
params_new = {
    'L': L_new,
    't': t_new,
    'r': r_new,
    'fee': fee_new,
    'early_rate': early_rate_new,
    'default_rate': default_rate_new,
    'lgd': lgd_new,
    'prolong_pen': prolong_pen_new,
    'prolong_term': prolong_term_new,
    'ins_pen': ins_pen_new,
    'ins_sum': ins_sum_new,
    'cross_pen': cross_pen_new,
    'cross_sum': cross_sum_new,
    'money_transfer_cost': money_transfer_cost,
    'collection_rate': collection_rate,
    'collection_cost_rate': collection_cost_rate,
    'funding_rate': funding_rate,
    'repay_fee_inc': repay_fee_inc,
    'repay_fee_exp': repay_fee_exp,
    'portfolio_sale_rate': portfolio_sale_rate,
    'portfolio_sale_price': portfolio_sale_price,
    'tax_rate': tax_rate,
    # Для новых
    'cac_direct': cac_direct_new,
    'sms_count': sms_count_new,
    'sms_price': sms_price_new,
    'kc_cost': kc_cost_new,
    'scoring_cost': scoring_cost_new,
    'ident_cost': ident_cost_new,
    'AR': AR,
    'TR': TR,
    'lead_price': lead_price,
}

if use_repeat:
    params_repeat = {
        'L': L_repeat,
        't': t_repeat,
        'r': r_repeat,
        'fee': fee_repeat,
        'early_rate': early_rate_repeat,
        'default_rate': default_rate_repeat,
        'lgd': lgd_repeat,
        'prolong_pen': prolong_pen_repeat,
        'prolong_term': prolong_term_repeat,
        'ins_pen': ins_pen_repeat,
        'ins_sum': ins_sum_repeat,
        'cross_pen': cross_pen_repeat,
        'cross_sum': cross_sum_repeat,
        'money_transfer_cost': money_transfer_cost,
        'collection_rate': collection_rate,
        'collection_cost_rate': collection_cost_rate,
        'funding_rate': funding_rate,
        'repay_fee_inc': repay_fee_inc,
        'repay_fee_exp': repay_fee_exp,
        'portfolio_sale_rate': portfolio_sale_rate,
        'portfolio_sale_price': portfolio_sale_price,
        'tax_rate': tax_rate,
        # Для повторного (абсолютные, без деления)
        'cac_direct': cac_repeat,
        'sms_count': sms_count_repeat,
        'sms_price': sms_price_repeat,
        'kc_cost': kc_cost_repeat,
        'scoring_cost': scoring_cost_repeat,
        'ident_cost': ident_cost_repeat,
        'AR': 1.0,
        'TR': 1.0,
        'lead_price': 0,
    }
else:
    params_repeat = None

# Расчёт
profit_new, rev_new, cost_new, profit_before_new = calculate_loan(params_new, is_new=True)
if use_repeat and params_repeat:
    profit_repeat, rev_rep, cost_rep, profit_before_rep = calculate_loan(params_repeat, is_new=False)
    ltv = profit_new + profit_repeat * RR
    # CAC_total = CAC_new + RR * CAC_repeat
    cac_new_total = (cac_direct_new + sms_count_new * sms_price_new + kc_cost_new
                     + (scoring_cost_new / AR / TR) + (ident_cost_new / AR / TR))
    cac_repeat_total = (cac_repeat + sms_count_repeat * sms_price_repeat + kc_cost_repeat
                        + scoring_cost_repeat + ident_cost_repeat)   # для повторного нет деления
    cac_total = cac_new_total + RR * cac_repeat_total
else:
    profit_repeat = 0
    ltv = profit_new
    cac_total = (cac_direct_new + sms_count_new * sms_price_new + kc_cost_new
                 + (scoring_cost_new / AR / TR) + (ident_cost_new / AR / TR))

ltv_cac_ratio = ltv / cac_total if cac_total > 0 else 0

# --------------------------------------------------------------
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# --------------------------------------------------------------
st.header("📈 Результаты")
col1, col2, col3 = st.columns(3)
col1.metric("LTV (чистая прибыль)", f"{ltv:,.0f} ₽")
col2.metric("CAC (полный, с учётом повторов)", f"{cac_total:,.0f} ₽")
col3.metric("LTV / CAC", f"{ltv_cac_ratio:.2f}")

st.subheader("📊 Детализация по новому займу")
df_rev_new = pd.DataFrame(rev_new.items(), columns=["Статья", "Сумма (₽)"])
st.dataframe(df_rev_new, use_container_width=True, hide_index=True)
df_cost_new = pd.DataFrame(cost_new.items(), columns=["Статья", "Сумма (₽)"])
st.dataframe(df_cost_new, use_container_width=True, hide_index=True)
st.metric("Прибыль до налогов (новый)", f"{profit_before_new:,.0f} ₽")
st.metric("Прибыль после налогов (новый)", f"{profit_new:,.0f} ₽")

if use_repeat and params_repeat:
    st.subheader("🔄 Детализация по повторному займу")
    df_rev_rep = pd.DataFrame(rev_rep.items(), columns=["Статья", "Сумма (₽)"])
    st.dataframe(df_rev_rep, use_container_width=True, hide_index=True)
    df_cost_rep = pd.DataFrame(cost_rep.items(), columns=["Статья", "Сумма (₽)"])
    st.dataframe(df_cost_rep, use_container_width=True, hide_index=True)
    st.metric("Прибыль до налогов (повторный)", f"{profit_before_rep:,.0f} ₽")
    st.metric("Прибыль после налогов (повторный)", f"{profit_repeat:,.0f} ₽")
    st.caption(f"Вклад повторного займа в LTV: {profit_repeat * RR:,.0f} ₽ (RR = {RR:.2f})")
    st.caption(f"CAC нового: {cac_new_total:,.0f} ₽, CAC повторного: {cac_repeat_total:,.0f} ₽ → итоговый CAC = {cac_new_total:.0f} + {RR:.2f}*{cac_repeat_total:.0f} = {cac_total:.0f} ₽")

# Графики
fig1 = px.bar(df_rev_new, x="Статья", y="Сумма (₽)", title="Структура доходов (новый заём)", color_discrete_sequence=['#2ecc71'])
st.plotly_chart(fig1, use_container_width=True)
fig2 = px.bar(df_cost_new, x="Статья", y="Сумма (₽)", title="Структура расходов и потерь (новый заём)", color_discrete_sequence=['#e74c3c'])
st.plotly_chart(fig2, use_container_width=True)

st.caption("Модель включает все параметры: новый и повторный займы, CAC для повторного, отказной трафик, продажу просрочки, комиссии за погашение.")