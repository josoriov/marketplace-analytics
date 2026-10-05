{% test nonempty(model) %}
    select 1 where not exists (select 1 from {{ model }})
{% endtest %}

{% test unique_columns(model, columns) %}
    select {{ columns | join(', ') }}
    from {{ model }}
    group by {{ columns | join(', ') }}
    having count(*) > 1
{% endtest %}

{% test between(model, column_name, minimum, maximum=none) %}
    select {{ column_name }} from {{ model }}
    where {{ column_name }} < {{ minimum }}
    {% if maximum is not none %} or {{ column_name }} > {{ maximum }} {% endif %}
{% endtest %}
