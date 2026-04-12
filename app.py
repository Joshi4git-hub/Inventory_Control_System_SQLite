{% extends "base.html" %}
{% block title %}Shipments — Inventory Control System{% endblock %}

{% block content %}
<div class="page-header">
  <div>
    <h1>Shipment Schedule</h1>
    <p>Track delivery dates for low stock items and plan restocking.</p>
  </div>
  <div class="quick-actions">
    <a href="{{ url_for('view_products') }}" class="action-btn"><span class="icon">📋</span>View Products</a>
    <a href="{{ url_for('add_product') }}" class="action-btn"><span class="icon">➕</span>Add Product</a>
  </div>
</div>

<div class="card">
  <div class="card-title">Upcoming Shipments</div>

  {% if shipments %}
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Product</th>
          <th>Supplier</th>
          <th>Quantity</th>
          <th>ETA</th>
          <th>Arrival Date</th>
        </tr>
      </thead>
      <tbody>
        {% for s in shipments %}
        <tr>
          <td class="index-cell">{{ loop.index }}</td>
          <td class="name-cell">{{ s.name }}</td>
          <td>{{ s.supplier }}</td>
          <td>{{ s.quantity }}</td>
          <td><span class="badge badge-shipment">{{ s.eta_text }}</span></td>
          <td>{{ s.arrival_date }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <p class="view-meta">
    Showing {{ shipments|length }} low stock shipment{% if shipments|length != 1 %}s{% endif %}.
  </p>
  {% else %}
  <div class="empty-state">
    <h3>All stocked up</h3>
    <p>There are no low-stock products right now.</p>
    <p>
      <a href="{{ url_for('view_products') }}" class="text-link">Review products</a>
      or
      <a href="{{ url_for('add_product') }}" class="text-link">add new stock</a>.
    </p>
  </div>
  {% endif %}
</div>
{% endblock %}
