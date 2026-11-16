from odoo import models, fields, tools

class IndentProductDemandReport(models.Model):
    _name = 'indent.product.demand.report'
    _description = 'Product Demand MIS Report'
    _auto = False

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    period_type = fields.Selection(
        [('month', 'Month'), ('quarter', 'Quarter')],
        readonly=True
    )
    period = fields.Char(string='Period', readonly=True)
    # total_demand_qty = fields.Float(string='Total Demand', readonly=True)
    # available_qty = fields.Float(string='Available Stock', readonly=True)
    # shortage_qty = fields.Float(string='Shortage', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW indent_product_demand_report AS (

                WITH stock_qty AS (
                    SELECT
                        product_id,
                        SUM(quantity) AS available_qty
                    FROM stock_quant
                    WHERE location_id IN (
                        SELECT id FROM stock_location WHERE usage = 'internal'
                    )
                    GROUP BY product_id
                )

                -- ======================
                -- MONTHLY
                -- ======================
                SELECT
                    (l.product_id * 1000000
                     + EXTRACT(YEAR FROM date_trunc('month', i.request_date))::int * 100
                     + EXTRACT(MONTH FROM date_trunc('month', i.request_date))::int) AS id,

                    l.product_id,
                    'month' AS period_type,

                    TO_CHAR(date_trunc('month', i.request_date), 'YYYY-MM') AS period,

                    SUM(l.quantity) AS total_demand_qty,
                    COALESCE(s.available_qty, 0) AS available_qty,
                    GREATEST(
                        SUM(l.quantity) - COALESCE(s.available_qty, 0),
                        0
                    ) AS shortage_qty

                FROM indent_request_line l
                JOIN indent_request i ON i.id = l.indent_id
                LEFT JOIN stock_qty s ON s.product_id = l.product_id

                GROUP BY
                    l.product_id,
                    s.available_qty,
                    date_trunc('month', i.request_date)

                UNION ALL

                -- ======================
                -- QUARTERLY
                -- ======================
                SELECT
                    (l.product_id * 1000000
                     + EXTRACT(YEAR FROM date_trunc('quarter', i.request_date))::int * 10
                     + EXTRACT(QUARTER FROM date_trunc('quarter', i.request_date))::int
                     + 500000000) AS id,

                    l.product_id,
                    'quarter' AS period_type,

                    CONCAT(
                        EXTRACT(YEAR FROM date_trunc('quarter', i.request_date))::int,
                        '-Q',
                        EXTRACT(QUARTER FROM date_trunc('quarter', i.request_date))::int
                    ) AS period,

                    SUM(l.quantity) AS total_demand_qty,
                    COALESCE(s.available_qty, 0) AS available_qty,
                    GREATEST(
                        SUM(l.quantity) - COALESCE(s.available_qty, 0),
                        0
                    ) AS shortage_qty

                FROM indent_request_line l
                JOIN indent_request i ON i.id = l.indent_id
                LEFT JOIN stock_qty s ON s.product_id = l.product_id

                GROUP BY
                    l.product_id,
                    s.available_qty,
                    date_trunc('quarter', i.request_date)
            )
        """)

