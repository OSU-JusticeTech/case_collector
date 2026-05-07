.PHONY: erd

# Generate Django ER diagram
erd:
	python manage.py graph_models --pydot -o er.png