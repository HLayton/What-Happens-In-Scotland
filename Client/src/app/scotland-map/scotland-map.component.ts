import {Component, EventEmitter, Input, OnInit, Output, ViewEncapsulation} from '@angular/core';

declare let d3: any;
import * as topojson from 'topojson';

/**
 * Component for the generation and management of the Scotland Map
 */
@Component({
  selector: 'app-scotland-map',
  templateUrl: './scotland-map.component.html',
  styleUrls: ['./scotland-map.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class ScotlandMapComponent implements OnInit {

  @Input() region;

  // Emits the id of the region selected on the map to parent components
  @Output() regionSelected = new EventEmitter<string>();

  public regions = {};

  private margin = {top: 20, right: 20, bottom: 0, left: 50};
  private height: number;
  private width: number;
  private svg: any;
  private colour: any;
  private projection;
  private path: number;
  private tooltip: any;
  private offsetL: number;
  private offsetT: number;

  constructor() {
    this.width = 1000 - this.margin.left - this.margin.right;
    this.height = 1000 - this.margin.top - this.margin.bottom;
  }

  ngOnInit() {
    this.initVariables();
  }

  /**
   *
   */
  private initVariables (): void {

    this.projection = d3.geo.albers()
      .center([-0.0959, 57.90153])
      .rotate([4.1, 0])
      .parallels([50, 60])
      .scale(8000)
      .translate([this.width / 2, this.height / 2]);

    this.colour = d3.scale.linear()
      .domain([-1, /*-0.1, 0.1,*/0, 1])
      .range(['#ff000c', /*'#8f8f8f',*/ '#b2b2b2', '#0500ff']);

    // Create svg for graph to be drawn in
    this.svg = d3.select('#scotland-map')
      .append('svg')
      .attr('id', 'mapp')
      // Makes map resizeable
      .attr('preserveAspectRatio', 'xMinYMin meet')
      .attr('viewBox', '0 0 ' + this.width + ' ' + this.height);

    this.offsetL = document.getElementById('scotland-map').offsetLeft + 20;
    this.offsetT = document.getElementById('scotland-map').offsetTop + 20;

    this.path = d3.geo.path().projection(this.projection);

    this.tooltip = d3.select('#scotland-map')
      .append('div')
      .attr('class', 'tooltip hidden');

  }

  /**
   * Draws map when topology has been parsed
   * @param topology
   */
  public drawMap (topology: any): void {
    // Draw map outline
    // this.drawGlasgowOutline(topology);

    // Draw each region polygon
    this.drawRegions(topology);
  }

  /**
   * Draws the regions that exist in the topology passed in.
   * @param topology
   */
  private drawRegions (topology: any): void {
    this.svg.append('g').selectAll('path')
      .data(topology.features) // Read in the array of features from the topology data
      .enter()
      .append('path') // Add a path element
      // With classes regions and region id
      .attr('class', d => 'regions ' + d.properties.LAD13CD)
      // Define the outline of the shape based on the defined projection and polygon shape
      .attr('d', this.path)
      // Fill the polygon in with a colour from a range
      .attr('fill', d => this.colour(this.regions[d.properties.LAD13CD].average))
      .attr('id', d => d.properties.LAD13CD)
      .on('click', this.setData)
      .on('mousemove', this.showTooltip)
      .on('mouseout', () => {
        this.tooltip.classed('hidden', true);
      });
  }

  // /**
  //  * Draws the outline of the region in the topology passed in. Only draws outer boundaries
  //  * @param t
  //  */
  // private drawGlasgowOutline (t: any): void  {
  //   const topology = topojson.topology([t], null);
  //   this.svg.append('path')
  //   // Only returns the arcs that aren't shared by regions i.e the outer bounds
  //     .datum(topojson.mesh(topology, topology.objects[0], (a, b) => a === b ))
  //     .attr('d', this.path)
  //     .attr('stroke', () => this.colour(this.regions['glasgow-boundary'].average))
  //     .attr('id', 'glasgow-boundary')
  //     .attr('class', 'selected')
  //     .on('click', this.setData)
  //     .on('mousemove', this.showTooltip)
  //     .on('mouseout', () => {
  //       this.tooltip.classed('hidden', true);
  //     });
  // }

  public drawPoint(coordArray: number[]): void {
    const coordinates = this.projection(coordArray);
    this.svg
      .append('circle')
      .attr('id', ('c' + coordinates[0] + coordinates[1]).replace(/\./g, ''))
      .attr('cx', () => coordinates[0])
      .attr('cy', () => coordinates[1])
      .attr('r', '4px')
      .attr('fill', '#2a2727')
      .call(d => this.circlePulse(d[0][0]));
  }

  private circlePulse = (d: any): void => {
    this.svg.select('#' + d.id)
      .transition()
      .duration(2000)
      .attr('stroke-width', 0.5)
      .attr('r', 12)
      .ease('sine');
    // .transition()
    // .duration(5000)
    // .attr('stroke-width', 10)
    // .attr('r', 0)
    // .remove();
  }

  // Event Handlers //

  /**
   * Emits the id of the selected region
   * @param e
   */
  private setData = (e: any): void => {
    const id = e.properties ? e.properties.LAD13CD : 'scotland-boundary';
    this.regionSelected.emit(id);
  }

  /**
   * Displays the tooltip for the region hovered over at the appropriate place on the screen
   * @param d
   */
  private showTooltip = (d: any): void => {
    const label = (d.properties ? d.properties.LAD13NM : 'Scotland') +
      '<br> ' + this.regions[d.properties ? d.properties.LAD13CD : 'scotland-boundary'].prettyAverage + '% Happy';
    const mouse = d3.mouse(this.svg.node());
    // console.log(mouse, this.offsetL, this.offsetT);
    this.tooltip.classed('hidden', false)
      .attr('style', 'left:' + (mouse[0] + this.offsetL) + 'px;top:' + (mouse[1] + this.offsetT) + 'px')
      .html(label);
  }
}