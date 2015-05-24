import math
import numpy as np
from bokeh.charts import Bar
from bokeh.models import DataRange1d, GridPlot, Plot, PreviewSaveTool, Range1d
from bokeh.models.glyphs import AnnularWedge, Rect, Text
from bokeh.plotting import ColumnDataSource, output_file, show


def pie_chart(values, categories, colors, title, plot_width, legend_width, pie_slice_label=None):
    r"""Generate a pie chart.

    Generate a pie chart using the Bokeh library.

    The number of values, categories and colors must match. The labels shown on the pie slices are generated from
    `pie_slice_label`, which is formatted with Python's str.format method. You may refer to the percentage by
    '{0}' in the string. For example, if the percentage is 30.58 and `pie_slice_label` is '{0|.1f} %', then the string
    '30.6 %' is used as the label.

    No value must be negative, and at least one value must be non-zero.

    Parameters
    ----------
    values : array_like
        Values to plot on the pie chart. Values that are zero will be ignored.
    categories: array_like
        Categories corresponding to the values. These will be used in the legend.
    colors: array_like
        Colors corresponding to the categories.
    title: str
        Plot title.
    plot_width: int
        Width of the plot, in pixels.
    legend_width: int
        Width of the legend, in pixels.
    pie_slice_label: str, optional
        Label for a pie slice. Will be used with the str.format method.

    Returns
    -------
    Plot
        Bokeh plot containing the pie chart and its legend.

    Raises
    ------
    ValueError
        If any value is negative or a non-number, or if all values are zero, or if the number of values, categories and
        colors don't match.
    """

    # layout choices
    key_color_width = 30
    key_color_height = 16
    text_font = 'times'
    text_font_size = '13pt'
    plot_border = 10
    pie_legend_gap = 20
    legend_bottom_margin = 20

    # check that arguments are fine
    if len(values) != len(colors) or len(colors) != len(categories):
        raise ValueError('the number of values, colors and categories don\'t match')
    for v in values:
        if v < 0:
            raise ValueError('values must be non-negative: {0}'.format(v))


# convert values to angles and percentages
    angles = normalize(values, 2 * math.pi)
    percentages = normalize(values, 100.)

    # remove all zero values
    data = zip(angles, categories, colors, percentages)
    data = [item for item in data if item[0] != 0]
    colors = [item[2] for item in data]

    # collect start and end angles
    start_angles = []
    end_angles = []
    for i, item in enumerate(data):
        start_angles.append(0 if i == 0 else end_angles[i - 1])
        end_angles.append(start_angles[i] + item[0])
    start_angles = np.array(start_angles)
    end_angles = np.array(end_angles)
    mid_angles = 0.5 * (start_angles + end_angles)

    # plot dimensions
    pie_radius = (plot_width - 2 * plot_border - legend_width - pie_legend_gap) / 2
    plot_height = 20 + 2 * pie_radius
    plot_width = 20 + 2 * pie_radius + legend_width

    # create plot
    xdr = DataRange1d(start=0, end=1)
    ydr = DataRange1d(start=0, end=1)
    plot = Plot(
        x_range=xdr,
        y_range=ydr,
        title=None,
        background_fill="white",
        border_fill='white',
        outline_line_color='white',
        min_border=2,
        plot_width=plot_width,
        plot_height=plot_height)
    plot.add_tools(PreviewSaveTool())

    # create pie slices
    inner_radius = 0
    outer_radius = pie_radius
    pie_center = (plot_border + outer_radius, plot_border + outer_radius)
    source = ColumnDataSource(
        data=dict(
            x=pie_center[0] * np.ones(len(data)),
            y=pie_center[1] * np.ones(len(data)),
            inner_radius=inner_radius * np.ones(len(data)),
            outer_radius=outer_radius * np.ones(len(data)),
            start_angle=start_angles,
            end_angle=end_angles,
            fill_color=colors,
            category=[item[1] for item in data]
        )
    )
    a = AnnularWedge(x=dict(field='x', units='screen'),
                     y=dict(field='y', units='screen'),
                     inner_radius=dict(field='inner_radius', units='screen'),
                     outer_radius=dict(field='outer_radius', units='screen'),
                     start_angle=dict(field='start_angle'),
                     end_angle=dict(field='end_angle'),
                     fill_color=dict(field='fill_color'),
                     line_color='white')
    plot.add_glyph(source, a)

    # create the pie slice labels
    if pie_slice_label is not None:
        mid_radius = 0.5 * (inner_radius + outer_radius)
        xs_label = pie_center[0] + mid_radius * np.cos(mid_angles)
        ys_label = pie_center[1] + mid_radius * np.sin(mid_angles)
        label_source = ColumnDataSource(
            data=dict(
                x=xs_label,
                y=ys_label,
                text=[pie_slice_label.format(item[3]) for item in data]
            )
        )
        t = Text(x=dict(field='x', units='screen'),
                 y=dict(field='y', units='screen'),
                 text=dict(field='text', units='screen'),
                 text_font=text_font,
                 text_font_size=text_font_size,
                 text_color='white',
                 text_align='center',
                 text_baseline='middle')
        plot.add_glyph(label_source, t)

    # create the legend colors
    xs_legends = np.array([pie_center[0] + pie_radius + pie_legend_gap + key_color_width / 2 for _ in range(len(data))])
    ys_legends = np.array([pie_center[1] - pie_radius + legend_bottom_margin + 30 * i + key_color_height / 2 for i in range(len(data))])
    legend_color_width = 30
    legend_color_height = 15
    key_color_source = ColumnDataSource(
        data=dict(
            x=xs_legends,
            y=ys_legends,
            width=legend_color_width * np.ones(len(data)),
            height=legend_color_height * np.ones(len(data)),
            fill_color=[color for color in reversed(colors)]
        )
    )
    r = Rect(x=dict(field='x', units='screen'),
             y=dict(field='y', units='screen'),
             width=dict(field='width', units='screen'),
             height=dict(field='height', units='screen'),
             line_color=dict(field='fill_color'),
             fill_color=dict(field='fill_color'))
    plot.add_glyph(key_color_source, r)

    # create the legend labels
    key_label_source = ColumnDataSource(
        data=dict(
            x=legend_color_width + 10 + xs_legends,
            y=ys_legends,
            text=[item[1] for item in reversed(data)]
        )
    )
    t = Text(x=dict(field='x', units='screen'),
             y=dict(field='y', units='screen'),
             text=dict(field='text', units='screen'),
             text_font=text_font,
             text_font_size=text_font_size,
             text_color='black',
             text_align='left',
             text_baseline='middle')
    plot.add_glyph(key_label_source, t)

    # title plot
    t_plot = title_plot(title, plot_width)

    # create a grid plot
    # we do this as grid plots don't feature the Bokeh logo and display the tool icons on the side
    grid = GridPlot(children=[[t_plot], [plot]], title=None)
    return grid


def stacked_bar_chart(values, categories, colors, x_label, y_label, title, plot_width, plot_height, legend_height):
    r"""Generate a stacked bar chart.

    Generate a stacked bar chart with the Bokeh library.

    The values must be a dictionary of lists. For example,

    values = dict(engineering=[1.2, 7.8, 3.8],
                  science=[10., 2.5])

    The number of keys for this dictionary must equal the number of colors.

    The categories will be used as the labels for the x axis.

    The legend height is an estimate of the vertical space required for the legend, in pixels. It is used to ensure that
    the legend isn't plotted on top of a bar.

    Parameters
    ----------
    values : array_like
        Values to plot on the pie chart. Values that are zero will be ignored.
    categories: array_like
        Categories corresponding to the values. These will be used in the legend.
    colors: array_like
        Colors corresponding to the categories.
    x_label: str
        Label for the x axis.
    y_label: str
        Label for the y axis.
    title: str
        Plot title.
    plot_width: int
        Width of the plot, in pixels.
    legend_height: int
        Height of the legend, in pixels.

    Returns
    -------
    Plot
        Bokeh plot.

    Raises
    ------
    ValueError
        If the number of colors and keys in `values` don't match, or if any value is negative, or if the legend height
        isn't smaller than the plot height.
    """

    # check that arguments are fine
    if len(values.keys()) != len(colors):
        raise ValueError('the number of value keys and colors don\'t match')
    for key in values:
        for v in values[key]:
            if v < 0:
                raise ValueError('all values must be non-negative')
    if legend_height >= plot_height:
        raise ValueError('the legend height must be smaller than the plot height')

    # ensure there is space for the legend
    max_value = max([sum([values[key][i] for key in values.keys()]) for i in range(len(values.keys()[0]))])
    max_y = max_value * plot_height / (plot_height - legend_height)
    ydr = Range1d(start=0, end=max_y)

    # bar plot
    plot = Bar(values=values,
               cat=categories,
               palette=colors,
               stacked=True,
               legend=True,
               xlabel=x_label,
               ylabel=y_label,
               title=None,
               width=plot_width,
               height=plot_height,
               continuous_range=ydr,
               tools='previewsave')

    # title plot
    t_plot = title_plot(title, plot_width)

    # create a grid plot
    # we do this as grid plots don't feature the Bokeh logo and display the tool icons on the side
    grid = GridPlot(children=[[t_plot], [plot]], title=None)
    return grid

def title_plot(title, width):
    r"""Generate a plot just containing a title.

    The generated plot just contains a title. The title may contain newline characters.

    Parameters
    ----------
    title : str
        Title.
    width: int
        Plot width, in pixels

    Returns
    -------
    Plot
        Bokeh plot containing the title.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.
    """

    # layout choices
    plot_border = 5
    line_height = 30
    text_font = 'times'
    text_font_size = '14pt'

    # figure out the text position and plot height
    lines = [line for line in reversed(title.split('\n'))]
    line_xs = [width / 2 for _ in range(len(lines))]
    line_ys = [plot_border + i * line_height for i, _ in enumerate(lines)]
    height = 2 * plot_border + len(lines) * line_height

    # create the plot
    xdr = DataRange1d(start=0, end=1)
    ydr = DataRange1d(start=0, end=1)
    plot = Plot(x_range=xdr,
                y_range=ydr,
                title=None,
                background_fill="white",
                border_fill='white',
                outline_line_color='white',
                min_border=2,
                plot_width=width,
                plot_height=height)
    plot.add_tools(PreviewSaveTool())

    # add the title
    source = ColumnDataSource(
        data=dict(
            x=line_xs,
            y=line_ys,
            text=lines
        )
    )
    t = Text(x=dict(field='x', units='screen'),
             y=dict(field='y', units='screen'),
             text=dict(field='text', screen='units'),
             text_font=text_font,
             text_font_size=text_font_size,
             text_color='black',
             text_align='center',
             text_baseline='bottom')
    plot.add_glyph(source, t)

    return plot


def normalize(values, normalized_total):
    r"""Normalize a list of values.

    The values are scaled so that their sum is equal to `normalized_total`, and a list of the scaled values is returned.

    Parameters
    ----------
    values : array_like
        Numerical values to normalize.
    normalized_total: number
        Sum of the scaled values.

    Returns
    -------
    list
        Normalized values.

    Raises
    ------
    ValueError
        If any of the values or the total is a non-number, or if all values are zero.

    Examples
    --------
    >>> normalize([1, 2], 2 * math.pi)
    [2.0943951023931953, 4.1887902047863905]

    >>> normalize([1, 0, 1], 100)
    [50.0, 0.0, 50.0]

    >>> normalize([0, 0], 1)
    Traceback (most recent call last):
    ...
    ValueError: at least one value must be non-zero
    """

    # make sure we have numbers
    values = [float(v) for v in values]
    normalized_total = float(normalized_total)

    # check for negative values
    for v in values:
        if v < 0:
            raise ValueError('negative values are not allowed: {0}'.format(v))

    # there must be non-zero values
    total = sum(values)
    if total == 0:
        raise ValueError('at least one value must be non-zero')

    # normalize
    return [normalized_total * v / total for v in values]
